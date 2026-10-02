#!/usr/bin/env python3
"""CPU-only fixed-input sufficiency audit. See frozen protocol.json."""
import contextlib, copy, csv, datetime, hashlib, inspect, json, os, pickle
import platform, queue, random, resource, signal, statistics, subprocess, sys
import textwrap, time, traceback, tracemalloc
from pathlib import Path

import os
HERE = Path(os.environ['OE_OUTPUT'])
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'reproduce/_common'))
from small_graph import manager, flat_shadow, field
from common import compact, position_segments, covers_position
from conservative_reduction import make, dominates
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.shadow import OutBound
from shapely.geometry import Point

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, x): Path(p).write_text(json.dumps(x, indent=2, sort_keys=True)+'\n')
PROTOCOL = json.loads((HERE/'protocol.json').read_text())
for name, expected in PROTOCOL['input_sha256'].items():
    assert sha(ROOT/name)==expected, ('input_changed', name)
SAVED = ROOT/'fixtures/controlled'
REFS = pickle.loads((SAVED/'reference.pkl').read_bytes())
STATES = pickle.loads((SAVED/'implementation_states.pkl').read_bytes())
ORIGINAL = ShadowUtils._update_shadow
SOURCE = textwrap.dedent(inspect.getsource(ORIGINAL))
from rss_shadow_key_control import install
STRUCTURAL_SOURCE = install()
STRUCTURAL = ShadowUtils._update_shadow
ShadowUtils._update_shadow = ORIGINAL
GUARD, GUARD_SOURCE = make(ORIGINAL)

def compiled(source, filename):
    scope = dict(ORIGINAL.__globals__)
    exec(compile(source, filename, 'exec'), scope)
    return scope['_update_shadow']

ADMISSION_SOURCE = SOURCE.replace('if new_shadow_begin not in bwd_searched_begin:',
                                 'if True:  # targeted backward admission disabled')
assert SOURCE.count('if new_shadow_begin not in bwd_searched_begin:')==2
ALL_SOURCE = ADMISSION_SOURCE.replace('if bound_lane_id in bwd_visited_lane:',
                                    'if False:  # backward visited reduction disabled')
ALL_SOURCE = ALL_SOURCE.replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)',
                              'return False  # backward mature-output reduction disabled')
FUNCTIONS = {'original': ORIGINAL, 'structural_key': STRUCTURAL,
             'mature_guard': GUARD,
             'admission_disabled': compiled(ADMISSION_SOURCE, 'admission_disabled.py'),
             'all_backward_reductions_disabled': compiled(ALL_SOURCE, 'all_backward_reductions_disabled.py')}
SOURCES = dict(original=SOURCE, structural_key=STRUCTURAL_SOURCE, mature_guard=GUARD_SOURCE,
               admission_disabled=ADMISSION_SOURCE, all_backward_reductions_disabled=ALL_SOURCE)
(HERE/'generated_sources').mkdir(exist_ok=True)
for name, source in SOURCES.items(): (HERE/'generated_sources'/ (name+'.py')).write_text(source)

def output_signature(shadows):
    return hashlib.sha256(json.dumps([compact(s) for s in shadows],sort_keys=True).encode()).hexdigest()

def timeout_handler(signum, frame): raise TimeoutError('administrative_30s_repetition_cap')

@contextlib.contextmanager
def instrumentation(enabled):
    metrics = dict(queues=[], primitive_calls={'forward':0,'backward':0},
                   guard_checks=0, guard_true=0, guard_unsupported=0, aggregate_peak_items=0)
    old_q = queue.Queue
    old_fwd, old_bwd = ShadowUtils._update_fwd_shadow, ShadowUtils._update_bwd_shadow
    old_dom = GUARD.__globals__['dominates']
    active = [0]
    class CountQueue(old_q):
        def __init__(self,*args,**kwargs):
            old_q.__init__(self,*args,**kwargs)
            self.record=dict(puts=0,gets=0,peak_items=0)
            metrics['queues'].append(self.record)
        def put(self,*args,**kwargs):
            value=old_q.put(self,*args,**kwargs)
            self.record['puts']+=1
            self.record['peak_items']=max(self.record['peak_items'],self.qsize())
            active[0]+=1
            metrics['aggregate_peak_items']=max(metrics['aggregate_peak_items'],active[0])
            return value
        def get(self,*args,**kwargs):
            value=old_q.get(self,*args,**kwargs)
            self.record['gets']+=1; active[0]-=1
            return value
    def fwd(*args,**kwargs):
        metrics['primitive_calls']['forward']+=1
        return old_fwd(*args,**kwargs)
    def bwd(*args,**kwargs):
        metrics['primitive_calls']['backward']+=1
        return old_bwd(*args,**kwargs)
    def dom(a,b):
        metrics['guard_checks']+=1
        ar,br=a.root,b.root
        supported=(not a.risk_bound and not b.risk_bound and
                   type(ar).__name__=='InOutBound' and type(br).__name__=='InOutBound' and
                   not ar.child_node and not br.child_node and
                   ar.ds_in_hist is None and br.ds_in_hist is None and
                   ar.t_in_hist is None and br.t_in_hist is None)
        metrics['guard_unsupported']+=int(not supported)
        result=old_dom(a,b); metrics['guard_true']+=int(result)
        return result
    if enabled:
        queue.Queue=CountQueue
        ShadowUtils._update_fwd_shadow=fwd; ShadowUtils._update_bwd_shadow=bwd
        GUARD.__globals__['dominates']=dom
    try: yield metrics
    finally:
        queue.Queue=old_q
        ShadowUtils._update_fwd_shadow=old_fwd; ShadowUtils._update_bwd_shadow=old_bwd
        GUARD.__globals__['dominates']=old_dom

CASES = {
    'pipeline_two_lanes':(True,False,'normal','base'),
    'pipeline_reversed_queue':(True,True,'normal','base'),
    'no_lane_crossing':(False,False,'normal','base'),
    'no_visibility_island':(True,False,'no_island','base'),
    'redundant_equal_copy':(True,False,'normal','duplicate'),
    'redundant_contained_cover':(True,False,'normal','contained'),
    'redundant_contained_cover_reversed':(True,True,'normal','contained')}

def assess(shadows, m, layer, t):
    start=time.perf_counter()
    seg=position_segments(shadows,m.road_network)
    implicit=any(x['implicit_tail'] for x in seg)
    non_lane1=any(s.root.id!=1 for s in shadows)
    unsupported=implicit or non_lane1
    position_missing=[(q,v) for q,v in layer if not covers_position(seg,1,float(-q))]
    if unsupported:
        state_missing=None
    else:
        geoms=[(s.root.ds_out,m.bwd_shadow_FRS(s,t,t)) for s in shadows]
        geoms=[(ds,g.buffer(1e-9)) for ds,g in geoms if g is not None]
        state_missing=sum(not any(g.covers(Point(float(q)+ds,float(v))) for ds,g in geoms)
                          for q,v in layer)
    return dict(reference_count=len(layer), position_missing=len(position_missing) if not implicit else None,
                position_raw_absence=len(position_missing), position_speed_missing=state_missing,
                semantic_status='unresolved_decoder_scope' if unsupported else 'finite_tested',
                implicit_tail=implicit, non_lane1_root=non_lane1,
                stationary_witness_position_missing=not bool(covers_position(seg,1,8)),
                coverage_audit_ms=(time.perf_counter()-start)*1000,
                output= [compact(s) for s in shadows])

def execute(job, variant, mode, rep):
    record=dict(job=job,variant=variant,mode=mode,repetition=rep,status='started',epochs=[])
    rows=record['epochs']; steps=[]; history=[]
    is_stress=job.startswith('duplicate_')
    if is_stress:
        connected,reverse,visibility,representation=True,False,'normal','base'
        times=[3.0]; refcase='pipeline_two_lanes'
    else:
        connected,reverse,visibility,representation=CASES[job]
        times=REFS[job]['times'];refcase=job
    m=manager(connected)
    def vis(lane,ds,data,pose,t):
        if visibility=='no_island' and t in [2.5,3.0]:
            return lane.lanelet_id==2 or ds<=3 or ds>=15
        return field(lane,ds,data,pose,t)
    try:
        signal.alarm(30)
        with instrumentation(mode=='instrumented') as met:
            for t in times:
                input_start=time.perf_counter()
                if is_stress:
                    saved=copy.deepcopy(STATES[('pipeline_two_lanes','mature_coverage_guard')][5])
                    base=m.predict_shadow(saved,t)
                    work=[s for _ in range(int(job.split('_')[1])) for s in copy.deepcopy(base)]
                elif t==0:
                    s=flat_shadow();s.root=OutBound(1,0,0);s.leaf_list=[];s.leaf_depth=[];work=[s]
                else: work=m.predict_shadow(history,t)
                if t==2.5 and representation!='base':
                    assert len(history)==1
                    extra=copy.deepcopy(history[0])
                    if representation=='contained': extra.root.ds_out=9.;extra.leaf_depth=[6.]
                    assert dominates(history[0],extra)
                    work.extend(m.predict_shadow([extra],t))
                if reverse: work=list(reversed(work))
                q=queue.Queue()
                for s in work:q.put(s)
                input_ms=(time.perf_counter()-input_start)*1000
                before_queues=len(met['queues'])
                if mode=='memory':tracemalloc.start()
                started=time.perf_counter()
                maps,history=FUNCTIONS[variant](m,q,vis,None,None,t)
                elapsed=(time.perf_counter()-started)*1000
                mem=None
                if mode=='memory':
                    mem=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
                row=dict(t=t,input_count=len(work),output_count=len(history),update_ms=elapsed,
                         input_preparation_ms=input_ms,python_peak_additional_bytes=mem,
                         output_digest=output_signature(history),queue_empty=q.empty())
                if mode=='instrumented':
                    # q record is the last-created queue before update; subsequent are primitive internals.
                    row['outer_queue']=copy.deepcopy(met['queues'][before_queues-1])
                    layer=REFS[refcase]['layers'][REFS[refcase]['times'].index(t)]
                    row['coverage']=assess(history,m,layer,t)
                rows.append(row)
            if mode=='instrumented':record['instrumentation']=copy.deepcopy(met)
        record.update(status='completed',terminated=True,total_update_ms=sum(x['update_ms'] for x in rows))
    except BaseException as exc:
        record.update(status='timeout' if isinstance(exc,TimeoutError) else 'invalid',terminated=False,
                      error=repr(exc),traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        if tracemalloc.is_tracing():tracemalloc.stop()
    return record

def main():
    signal.signal(signal.SIGALRM,timeout_handler)
    jobs=list(CASES)+['duplicate_'+str(n) for n in [1,4,16,64]]
    manifest=dict(started_at_utc=datetime.datetime.utcnow().isoformat()+'Z',command=sys.argv,
                  python=sys.version,platform=platform.platform(),device='CPU; no GPU APIs',
                  protocol_sha256=sha(HERE/'protocol.json'),source_sha256=sha(__file__),
                  native_revision='2b6b06637850b406cfbeab926a3dedc01edad91e',
                  env={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','CUDA_VISIBLE_DEVICES']},
                  generated_source_sha256={k:sha(HERE/'generated_sources'/(k+'.py')) for k in FUNCTIONS})
    dump(HERE/'manifest.json',manifest)
    rawpath=HERE/'runs.jsonl'
    if rawpath.exists(): raise RuntimeError('raw run file exists; never silently overwrite')
    warmups=[execute('pipeline_two_lanes',v,'warmup',0) for v in FUNCTIONS]
    dump(HERE/'warmups.json',warmups)
    rng=random.Random(PROTOCOL['seed']);schedule=[]
    for rep in range(11):
        group=[(job,v,'timing',rep) for job in jobs for v in FUNCTIONS];rng.shuffle(group);schedule+=group
    for mode in ['instrumented','memory']:
        group=[(job,v,mode,0) for job in jobs for v in FUNCTIONS];rng.shuffle(group);schedule+=group
    dump(HERE/'execution_schedule.json',schedule)
    results=[]
    with rawpath.open('w') as out:
        for idx,args in enumerate(schedule):
            r=execute(*args);results.append(r);out.write(json.dumps(r,sort_keys=True)+'\n');out.flush()
            if idx%25==0 or r['status']!='completed':
                print(json.dumps(dict(index=idx,total=len(schedule),job=args[0],variant=args[1],mode=args[2],status=r['status'])),flush=True)
    summary=[]
    for job in jobs:
        for variant in FUNCTIONS:
            group=[x for x in results if x['job']==job and x['variant']==variant]
            good=[x for x in group if x['status']=='completed']
            timed=[x for x in good if x['mode']=='timing']
            inst=next((x for x in good if x['mode']=='instrumented'),None)
            memory=next((x for x in good if x['mode']=='memory'),None)
            signatures={tuple(e['output_digest'] for e in x['epochs']) for x in good}
            vals=sorted(x['total_update_ms'] for x in timed)
            row=dict(job=job,variant=variant,total_runs=len(group),completed=len(good),invalid=sum(x['status']=='invalid' for x in group),
                     timeout=sum(x['status']=='timeout' for x in group),output_parity=len(signatures)==1,
                     timing_n=len(vals),update_total_median_ms=statistics.median(vals) if vals else None,
                     update_total_min_ms=min(vals) if vals else None,update_total_max_ms=max(vals) if vals else None,
                     update_total_p90_ms=vals[int(.9*(len(vals)-1))] if vals else None,
                     timed_max_epoch_ms=max((e['update_ms'] for x in timed for e in x['epochs']),default=None))
            if inst:
                last=inst['epochs'][-1]; met=inst['instrumentation']
                row.update(target_t=last['t'],reference_count=last['coverage']['reference_count'],
                           position_missing=last['coverage']['position_missing'],position_speed_missing=last['coverage']['position_speed_missing'],
                           semantic_status=last['coverage']['semantic_status'],output_count=last['output_count'],
                           worklist_gets=sum(e['outer_queue']['gets'] for e in inst['epochs']),
                           peak_worklist=max(e['outer_queue']['peak_items'] for e in inst['epochs']),
                           all_queue_gets=sum(q['gets'] for q in met['queues']),aggregate_peak_queue_items=met['aggregate_peak_items'],
                           primitive_calls=sum(met['primitive_calls'].values()),guard_checks=met['guard_checks'],
                           guard_true=met['guard_true'],guard_unsupported=met['guard_unsupported'],
                           offline_coverage_total_ms=sum(e['coverage']['coverage_audit_ms'] for e in inst['epochs']))
            if memory:row['python_update_peak_additional_bytes']=max(e['python_peak_additional_bytes'] for e in memory['epochs'])
            summary.append(row)
    dump(HERE/'summary.json',summary)
    keys=sorted({k for r in summary for k in r})
    with (HERE/'summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(summary)
    manifest.update(finished_at_utc=datetime.datetime.utcnow().isoformat()+'Z',scheduled=len(schedule),
                    completed=sum(r['status']=='completed' for r in results),invalid=sum(r['status']=='invalid' for r in results),
                    timeout=sum(r['status']=='timeout' for r in results),all_output_parity=all(r['output_parity'] for r in summary),
                    process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    process_rss_scope='whole audit process including imports/offline reference/coverage; not per-method update memory')
    dump(HERE/'manifest.json',manifest)
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':main()
