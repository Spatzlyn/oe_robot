#!/usr/bin/env python3
"""Bounded native-genesis discovery; never constructs a mature branch forest."""
import copy, datetime, hashlib, inspect, json, pickle, queue, random, signal, sys, textwrap, traceback
from pathlib import Path
import os
HERE=Path(os.environ['OE_OUTPUT']); ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reproduce/_common'))
from small_graph import manager,Lane,Network
from common import compact,position_segments,covers_position
from risk_analysis.shadow_utils import ShadowUtils

ORIGINAL=ShadowUtils._update_shadow
SOURCE=textwrap.dedent(inspect.getsource(ORIGINAL))
OFF_SOURCE=SOURCE.replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)','return False # mature-only OFF')
scope=dict(ORIGINAL.__globals__);exec(compile(OFF_SOURCE,'mature_only_off.py','exec'),scope);OFF=scope['_update_shadow']
SEED=240925

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def forest(ss):return [compact(x) for x in ss]

def setup(trunk=0):
    m=manager();lanes=[Lane(100,20,successor=[101]),Lane(101,20,predecessor=[100]),Lane(1,20,predecessor=[5] if trunk else [2,3]),Lane(2,20,successor=[5] if trunk else [1]),Lane(3,20,successor=[5] if trunk else [1])]
    if trunk:lanes.append(Lane(5,trunk,predecessor=[2,3],successor=[1]))
    for l in lanes:
        if l.lanelet_id in [100,101]:l.cross=[1]
    m.road_network=Network(lanes);m.risky_lane=[]
    return m

def fields(schedule,epoch):
    r,b2,b3=schedule[epoch]
    def vis(lane,ds,*_):
        id=lane.lanelet_id
        if id in [100,101]:return ds>=15 or ds<=3
        if id==5:return False
        c,island=(r if id==1 else b2 if id==2 else b3)
        if id==1:return ds<=c or (island==1 and 10<=ds<=10.5) or (island==2 and 15<=ds<=15.5)
        return ds>=15 or ds<=c or (island==1 and 4<=ds<=4.5) or (island==2 and 6<=ds<=6.5)
    return vis

def support(ss,m):
    seg=position_segments(ss,m.road_network)
    # A terminal InBound is bounded in a backward tree, not an implicit tail.
    ambiguous=[]
    for s in ss:
        if s.risk_bound:continue # forward roots only 100/101, no successor path into risk graph
        if any(d is None for d in s.leaf_depth):ambiguous.append(compact(s))
        def walk(n):
            if n.child_node:
                return all(walk(c) for c in n.child_node)
            return type(n).__name__ in ['InBound','InOutBound']
        if not walk(s.root):ambiguous.append(compact(s))
    return {str(i):{'present':bool(covers_position(seg,i,8.)),
                    'absence_supported':not ambiguous} for i in [2,3]},ambiguous

def signature(s):return set((int(l.id),None if d is None else float(d)) for l,d in zip(s.leaf_list,s.leaf_depth))

def run_case(case,trace=True,trunk=0):
    m=setup(trunk);events=[];epochs=[];popcount=[0];candidate_count=[0];active_epoch=[0]
    def emit(stage,**extra):
        if trace:events.append(dict(stage=stage,epoch=active_epoch[0],**extra))
    def repeat(sh,t,predicate,retained,pending):
        reject=bool(predicate(sh));sig=signature(sh)
        owners=[x for x in retained if not x.risk_bound and x.root.id==sh.root.id and x.root.ds_out==sh.root.ds_out]
        subset=[x for x in owners if signature(x)<sig]
        target=bool(reject and not sh.risk_bound and subset)
        candidate_count[0]+=int(target)
        emit('mature_reduction',t=t,rejected=reject,strict_subset_rejection=target,
             candidate=compact(sh),candidate_leaf_signatures=sorted(sig),
             retained=forest(retained),pending=forest(list(pending.queue)),
             target_witness_positions={str(i):bool(covers_position(position_segments([sh],m.road_network),i,8.)) for i in [2,3]})
        return reject
    def popped(s,t):
        popcount[0]+=1
        if popcount[0]>1000:raise RuntimeError('administrative work budget')
        emit('queue_pop',t=t,shadow=compact(s))
    code=SOURCE.replace('if not check_repeate(mature_shadow):','if not record_repeat(mature_shadow,t,check_repeate,mature_shadow_list,unprocessed_shadow_queue):')
    code=code.replace('bound_lane_id = cur_shadow.root.id','bound_lane_id = cur_shadow.root.id\n        record_pop(cur_shadow,t)')
    ctx=dict(ORIGINAL.__globals__,record_repeat=repeat,record_pop=popped)
    exec(compile(code,'native_traced.py','exec'),ctx);fn=ctx['_update_shadow'] if trace else ORIGINAL
    old_create=ShadowUtils.create_shadow;old_bwd=ShadowUtils._update_bwd_shadow
    def create(self,*args,**kw):
        s=old_create(self,*args,**kw);emit('native_create',args=list(args),shadow=compact(s));return s
    def bwd(self,s,*args,**kw):
        before=compact(s);out=old_bwd(self,s,*args,**kw)
        emit('backward_primitive',input=before,mature=compact(out[0]) if out[0] is not None else None,generated=forest(out[1]),visited=out[2]);return out
    if trace:ShadowUtils.create_shadow=create;ShadowUtils._update_bwd_shadow=bwd
    prior_handler=signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in ()).throw(TimeoutError('administrative 5s bound')))
    signal.alarm(5)
    row=dict(case=case['id'],schedule=case['schedule'],trunk=trunk,status='started',epochs=epochs,events=events)
    history=[];counterfactuals=[]
    try:
        for index,t in enumerate([0,.25,.5,.75,1.]):
            active_epoch[0]=index;popcount[0]=0;vis=fields(case['schedule'],index)
            # Continuous witness hidden by piecewise constant nearest-waypoint fields.
            for laneid in [2,3]:
                lane=m.road_network.find_lane_id(laneid)
                assert all(not vis(lane,ds) for ds in [7.5,8,8.5,9,9.5,10,10.5,11,11.5])
            before=forest(history)
            if not history:
                work=[m.create_shadow(100,18,None,t,'in',None)]
                genesis='native_initialization_form' if index==0 else 'native_empty_state_reinitialization'
            else:
                work=m.predict_shadow(history,t);genesis='native_predict_shadow'
            emit('epoch_input',t=t,generation=genesis,previous_forest=before,predicted_work=forest(work),risky_lanes=list(m.risky_lane))
            frozen_m=copy.deepcopy(m);frozen_work=copy.deepcopy(work)
            q=queue.Queue()
            for s in work:q.put(s)
            event_start=len(events);candidate_before=candidate_count[0]
            _,history=fn(m,q,vis,None,None,t)
            membership,ambiguous=support(history,m)
            er=dict(t=t,genesis=genesis,predicted_input=forest(frozen_work),final_forest=forest(history),
                    witness_membership=membership,implicit_uncertainty=ambiguous,
                    strict_subset_rejections=candidate_count[0]-candidate_before,queue_pops=popcount[0])
            if trace and candidate_count[0]>candidate_before:
                cq=queue.Queue()
                for s in copy.deepcopy(frozen_work):cq.put(s)
                oldtr=trace;trace=False
                try:_,repaired=OFF(frozen_m,cq,vis,None,None,t)
                finally:trace=oldtr
                cm,ca=support(repaired,frozen_m)
                er['mature_only_off_same_input']=dict(final_forest=forest(repaired),witness_membership=cm,implicit_uncertainty=ca)
                er['fixed_input_digest']=digest(forest(frozen_work))
                er['recovered_witnesses']=[i for i in ['2','3'] if not membership[i]['present'] and membership[i]['absence_supported'] and cm[i]['present']]
                counterfactuals.append(er['recovered_witnesses'])
            epochs.append(er)
        row.update(status='completed',strict_subset_rejections=candidate_count[0],
                   initial_witness_coverage={i:epochs[0]['witness_membership'][i]['present'] for i in ['2','3']},
                   positive_epochs=[e['t'] for e in epochs if e.get('recovered_witnesses')],
                   positive_witnesses=sorted(set(sum(counterfactuals,[]))))
    except Exception as exc:
        row.update(status='incomplete' if isinstance(exc,TimeoutError) or 'administrative' in str(exc) else 'invalid',error=repr(exc),traceback=traceback.format_exc())
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,prior_handler)
        ShadowUtils.create_shadow=old_create;ShadowUtils._update_bwd_shadow=old_bwd
    return row

def schedules():
    rng=random.Random(SEED);out=[]
    # 16 deterministic development templates before randomized bounded exploration.
    for k in range(16):
        schedule=[]
        for e in range(5):
            b=(k//4+e)%3 if k%4 else k//4%3
            schedule.append([[k%4,0 if k<8 else (e%2)+1],[0 if b==0 else 3,0],[0 if b==1 else 3,0]])
        out.append(dict(id='D_template_%03d'%k,schedule=schedule))
    for k in range(240):
        sch=[]
        for e in range(5):
            sch.append([[rng.choice([0,1,2,3,4,5,6]),rng.randrange(3)] for _ in range(3)])
        out.append(dict(id='D_seeded_%03d'%k,schedule=sch))
    return out

def main():
    proto=json.loads((HERE/'development_protocol.json').read_text())
    for p,h in proto['frozen_source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    cases=schedules();dump(HERE/'development_schedule.json',cases)
    out=HERE/'development';out.mkdir(exist_ok=False);rows=[]
    for case in cases:
        r=run_case(case);dump(out/(case['id']+'.json'),r)
        if r.get('strict_subset_rejections',0)>0:
            plain=run_case(case,trace=False)
            r['instrumentation_parity']=plain['status']==r['status'] and [e['final_forest'] for e in plain['epochs']]==[e['final_forest'] for e in r['epochs']]
            dump(out/(case['id']+'__plain.json'),plain);dump(out/(case['id']+'.json'),r)
        sr={k:v for k,v in r.items() if k not in ['events','epochs','schedule']};rows.append(sr)
        if len(rows)%16==0 or r.get('positive_epochs') or r['status']!='completed':print(json.dumps(sr),flush=True)
    dump(HERE/'development_summary.json',rows)
    dump(HERE/'manifest.json',dict(command=sys.argv,seed=SEED,device='CPU',harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256((HERE/'development_protocol.json').read_bytes()).hexdigest(),attempts=len(rows),completed=sum(x['status']=='completed' for x in rows),invalid=sum(x['status']=='invalid' for x in rows),incomplete=sum(x['status']=='incomplete' for x in rows),subset_pair_cases=sum(x.get('strict_subset_rejections',0)>0 for x in rows),positive_cases=sum(bool(x.get('positive_epochs')) for x in rows),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))

if __name__=='__main__':main()
