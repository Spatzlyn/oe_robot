#!/usr/bin/env python3
"""Native branch reduction scope audit; all files remain in the delivery bundle."""
import argparse,copy,csv,datetime,hashlib,inspect,json,queue,signal,subprocess,sys,textwrap,time
from pathlib import Path
import os
HERE=Path(os.environ['OE_OUTPUT'])
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reproduce/_common'))
from small_graph import manager,Lane,Network
from common import compact,position_segments,covers_position
from conservative_reduction import make
from risk_analysis.shadow import Shadow,OutBound,InBound,ShadowNode
from risk_analysis.shadow_utils import ShadowUtils
from rss_shadow_key_control import install


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compile_code(code,original,**extra):
    scope=dict(original.__globals__,**extra);exec(compile(code,'boundary_variant.py','exec'),scope);return scope['_update_shadow']

def methods():
    original=ShadowUtils._update_shadow
    source=textwrap.dedent(inspect.getsource(original))
    assert source.count('if new_shadow_begin not in bwd_searched_begin:')==2
    struct_source=install();struct=ShadowUtils._update_shadow;ShadowUtils._update_shadow=original
    guard,guard_source=make(original)
    off=source.replace('if new_shadow_begin not in bwd_searched_begin:','if True:  # targeted admission reduction disabled')
    alloff=off.replace('if bound_lane_id in bwd_visited_lane:','if False:  # backward visited reduction disabled').replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)','return False  # backward mature reduction disabled')
    return original,{name:code for name,code in [('original',source),('structural_key',struct_source),('mature_guard',guard_source),('admission_off',off),('backward_reductions_off',alloff)]},{'original':original,'structural_key':struct,'mature_guard':guard,'admission_off':compile_code(off,original),'backward_reductions_off':compile_code(alloff,original)}


def setup(case):
    m=manager();trunk=case['trunk_length'];branchids=sorted(set(sum(case['jobs'],[])))
    lanes=[Lane(1,20,predecessor=[5] if trunk else branchids)]
    if trunk:lanes.append(Lane(5,trunk,predecessor=branchids,successor=[1]))
    lanes.extend(Lane(i,20,successor=[5] if trunk else [1]) for i in branchids)
    m.road_network=Network(lanes);m.risky_lane=[x.lanelet_id for x in lanes]
    jobs=[]
    for ids in case['jobs']:
        s=Shadow();s.risk_bound=False;s.parent_id=999;s.root=OutBound(1,3,0)
        parent=s.root
        if trunk:
            node=ShadowNode(5);node.parent_node=parent;parent.child_node=[node];parent=node
        leaves=[InBound(i,15,0) for i in ids]
        for leaf in leaves:leaf.parent_node=parent
        parent.child_node=leaves;s.leaf_list=leaves;s.leaf_depth=[17+trunk+15]*len(leaves);jobs.append(s)
    def visibility(lane,ds,*args):
        if lane.lanelet_id==1:return ds<=3
        if lane.lanelet_id==5:return False
        return ds>=15
    witnesses=[dict(lane=i,front_ds=8.,rear_ds=11.,v=0.,a=0.,min_visible_clearance_m=3.75) for i in branchids]
    # Independent input/feasibility audit: no runtime output used as truth.
    for w in witnesses:
        assert any(w['lane'] in ids for ids in case['jobs'])
        assert 0<=w['front_ds']<w['rear_ds']<14.75<20
        lane=m.road_network.find_lane_id(w['lane'])
        assert all(not visibility(lane,float(ds)) for ds in [8,8.5,9,9.5,10,10.5,11])
    return m,jobs,visibility,witnesses


def run_case(case,name,source,original,fn,out):
    m,jobs,vis,witnesses=setup(case);initial=[compact(x) for x in jobs]
    events=[]
    # Record genuine decision site without replacing the native predicate.
    def repeat(sh,t,predicate,retained,pending):
        rejected=bool(predicate(sh))
        events.append(dict(stage='mature_reduction',time=t,candidate=compact(sh),rejected=rejected,retained=[compact(x) for x in retained],pending=[compact(x) for x in list(pending.queue)]))
        return rejected
    code=source.replace('if not check_repeate(mature_shadow):','if not record_repeat(mature_shadow,t,check_repeate,mature_shadow_list,unprocessed_shadow_queue):')
    assert code.count('if not record_repeat(')==2
    count=[0]
    def pop(sh,t):
        count[0]+=1
        if count[0]>1000:raise RuntimeError('work_budget_exceeded')
        events.append(dict(stage='pop',time=t,shadow=compact(sh)))
    code=code.replace('bound_lane_id = cur_shadow.root.id',"bound_lane_id = cur_shadow.root.id\n        record_pop(cur_shadow,t)")
    scope=dict(fn.__globals__,record_repeat=repeat,record_pop=pop)
    exec(compile(code,'boundary_traced.py','exec'),scope)
    q=queue.Queue()
    for s in jobs:q.put(s)
    prior=signal.signal(signal.SIGALRM,lambda a,b: (_ for _ in ()).throw(TimeoutError('30s resource timeout')));signal.alarm(30)
    start=time.perf_counter()
    try:
        maps,history=scope['_update_shadow'](m,q,vis,None,None,0.)
        elapsed=time.perf_counter()-start
        seg=position_segments(history,m.road_network)
        def explicit_supported(shadow):
            def bounded(node):
                if node.child_node:
                    return type(node).__name__ in ['OutBound','ShadowNode'] and all(bounded(c) for c in node.child_node)
                return type(node).__name__ in ['InBound','InOutBound']
            return bool(shadow.leaf_list) and len(shadow.leaf_list)==len(shadow.leaf_depth) and all(d is not None for d in shadow.leaf_depth) and bounded(shadow.root)
        implicit=not all(explicit_supported(s) for s in history)
        for segment in seg:
            segment['generic_decoder_tail_flag']=segment['implicit_tail']
            if segment['node_type']=='InBound':segment['implicit_tail']=False
        # This restricted decoder recognizes bounded terminal InBounds. A true
        # truncation (depth=None or unknown terminal node) stays unresolved.
        for w in witnesses:
            w['output_position_present']=bool(covers_position(seg,w['lane'],w['front_ds']))
            w['status']='present_position_only' if w['output_position_present'] else ('unresolved_implicit_tail' if implicit else 'witnessed_omission')
        row=dict(case=case['id'],method=name,status='completed',classification='unresolved' if implicit else ('witnessed_omission' if any(w['status']=='witnessed_omission' for w in witnesses) else 'validated_finite_stationary_positions'),
            witness_count=len(witnesses),omitted=sum(w['status']=='witnessed_omission' for w in witnesses),unresolved=sum(w['status'].startswith('unresolved') for w in witnesses),implicit_tail=implicit,queue_pops=count[0],terminal_shadows=len(history),mature_rejections=sum(x.get('rejected',False) for x in events),traced_wall_seconds=elapsed,
            completion_task=None,collision=None,full_position_speed='not_measured',input_feasibility='analytic stationary trajectories in constructed initial branches',
            final_forest=[compact(x) for x in history],segments=seg,witnesses=witnesses,events=events,initial_forest=initial)
    except Exception as exc:
        row=dict(case=case['id'],method=name,status='incomplete' if isinstance(exc,TimeoutError) or 'work_budget' in str(exc) else 'invalid',error=repr(exc),events=events,initial_forest=initial)
    finally:signal.alarm(0);signal.signal(signal.SIGALRM,prior)
    if row['status']=='completed':
        m2,jobs2,vis2,_=setup(case);q2=queue.Queue()
        for s2 in jobs2:q2.put(s2)
        _,plain=fn(m2,q2,vis2,None,None,0.)
        row['instrumentation_parity']=[compact(x) for x in plain]==row['final_forest']
        if not row['instrumentation_parity']:
            row['status']='invalid';row['error']='traced versus uninstrumented forest mismatch'
    (out/(case['id']+'__'+name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({k:v for k,v in row.items() if k not in ['events','initial_forest','final_forest','segments','witnesses']}),flush=True)
    return row


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['development','validation'],required=True);args=ap.parse_args()
    protocol=json.loads((HERE/'protocol.json').read_text());out=HERE/args.phase;out.mkdir(exist_ok=False)
    original,codes,fns=methods()
    source_hash={}
    for name,code in codes.items():
        p=out/(name+'.py');p.write_text(code);source_hash[name]=digest(p)
    rows=[]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        for case in protocol[args.phase]:
            for name in protocol['methods']:rows.append(run_case(case,name,codes[name],original,fns[name],out))
    finally:ShadowUtils._update_shadow=original
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    cols=['case','method','status','classification','witness_count','omitted','unresolved','implicit_tail','queue_pops','terminal_shadows','mature_rejections','traced_wall_seconds','full_position_speed','instrumentation_parity','error']
    with (out/'summary.csv').open('w') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');wr.writeheader();wr.writerows(rows)
    manifest=dict(command=sys.argv,phase=args.phase,started_utc=started,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_only=True,seed='deterministic constructed inputs; no RNG',map='synthetic lane graph; no CARLA map',source_revision='2b6b06637850b406cfbeab926a3dedc01edad91e',harness_sha256=digest(__file__),protocol_sha256=digest(HERE/'protocol.json'),sources=source_hash,attempts=len(rows),invalid=sum(x['status']=='invalid' for x in rows),incomplete=sum(x['status']=='incomplete' for x in rows))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':main()
