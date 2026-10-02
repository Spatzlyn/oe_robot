#!/usr/bin/env python3
"""Frozen small-graph counterexample, exact reference, and normal controls."""
import argparse,copy,datetime,inspect,json,pickle,queue,subprocess,sys,textwrap
from pathlib import Path
from fractions import Fraction as F
from small_graph import manager,flat_shadow,field
from common import ROOT,compact,position_segments,covers_position,sha,instrument_update
from reference import field_intervals,propagate,witness,clearance,hidden,transition
from conservative_reduction import make,dominates
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.shadow import OutBound

ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
OUT=args.output.resolve();OUT.mkdir(exist_ok=False)
times=[i/2 for i in range(9)]
inputs=dict(seed=0,times=times,v_max=15,acceleration_bounds=[-8,4],reference_controls=[-8,-4,0,4],
    footprint_m=3,state_coordinate='front q, footprint [q-3,q]; q=-ds on lane 1; q=10-ds on lane 2',
    lanes=[dict(id=1,length=20,successor=[2]),dict(id=2,length=10,predecessor=[1])],
    observation='nearest-waypoint cells, observations at specified times; no new hidden object births',
    finite_initial='front q=-12..-4 step .25; v=0..15 step 1; filter initial visibility',
    continuous_scope='Every reference path satisfies continuous dynamics; finite controls/initial grid underapproximate full continuous set')
(OUT/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
original=ShadowUtils._update_shadow
safe,code=make(original);(OUT/'conservative_shadow_reduction.py').write_text(code)
source=textwrap.dedent(inspect.getsource(original));(OUT/'original_update_shadow.py').write_text(source)
applied=[]
def target(sh,t):
    r=sh.root
    yes=not applied and t==3 and r.id==1 and getattr(r,'ds_in',None)==15 and r.ds_out==2
    if yes:applied.append(dict(t=t,shadow=compact(sh)))
    return yes
patched=source.replace('if new_shadow_begin not in bwd_searched_begin:',
    'if new_shadow_begin not in bwd_searched_begin or target(new_shadow,t):')
scope=dict(original.__globals__,target=target);exec(compile(patched,'single_admission.py','exec'),scope)
(OUT/'single_admission.py').write_text(patched)
from rss_shadow_key_control import install
structural_source=install();structural=ShadowUtils._update_shadow;ShadowUtils._update_shadow=original
(OUT/'structural_key.py').write_text(structural_source)

cases=[('pipeline_two_lanes',True,False,'normal','base'),
       ('pipeline_reversed_queue',True,True,'normal','base'),
       ('no_lane_crossing',False,False,'normal','base'),
       ('no_visibility_island',True,False,'no_island','base'),
       ('redundant_equal_copy',True,False,'normal','duplicate'),
       ('redundant_contained_cover',True,False,'normal','contained'),
       ('redundant_contained_cover_reversed',True,True,'normal','contained')]
summary=[];all_reference={};all_runs={}
for name,connected,reverse,visibility,representation in cases:
    m=manager(connected)
    def vis(lane,ds,data,pose,t):
        if visibility=='no_island' and t in [2.5,3.]:return lane.lanelet_id==2 or ds<=3 or ds>=15
        return field(lane,ds,data,pose,t)
    fields={};sample_rows=[]
    for t in times:
        samples=[]
        for lane in m.road_network.id_map.values():
            for ds in lane.waypoint_ds:
                q=-ds if lane.lanelet_id==1 else 10-ds
                value=bool(vis(lane,ds,None,None,t));samples.append((q,value))
                sample_rows.append(dict(t=t,lane=lane.lanelet_id,ds=float(ds),visible=value))
        # Both lane endpoints at q=0 are visible in these cases.
        fields[t]=field_intervals(dict(samples).items())
    initial=[(F(i,4),F(v)) for i in range(-48,-15) for v in range(16)]
    layers=propagate(initial,times,fields)
    reference=dict(counts=[len(x) for x in layers],fields={str(t):[[str(a),str(b)] for a,b in f] for t,f in fields.items()})
    all_reference[name]=dict(layers=layers,fields=fields,times=times)
    for variant,fn in [('original',original),('single_admission',scope['_update_shadow']),('structural_key',structural),('mature_coverage_guard',safe)]:
        m=manager(connected);applied.clear();history=[];steps=[];snapshots=[]
        ShadowUtils._update_shadow=fn
        try:
            for i,t in enumerate(times):
                if t==0:
                    s=flat_shadow();s.root=OutBound(1,0,0);s.leaf_list=[];s.leaf_depth=[]
                    work=[s]
                else:work=m.predict_shadow(history,t)
                if t==2.5 and representation!='base':
                    assert len(history)==1
                    extra=copy.deepcopy(history[0])
                    if representation=='contained':extra.root.ds_out=9.;extra.leaf_depth=[6.]
                    # Superset has the exact same inbound/time/history; no invented inbound at a cut.
                    assert dominates(history[0],extra)
                    work.extend(m.predict_shadow([extra],t))
                if reverse:work=list(reversed(work))
                q=queue.Queue()
                for s in work:q.put(s)
                maps,history=m._update_shadow(q,vis,None,None,t)
                segments=position_segments(history,m.road_network)
                missing=[s for s in layers[i] if not covers_position(segments,1,float(-s[0]))]
                steps.append(dict(t=t,shadows=[compact(s) for s in history],segments=segments,
                    reference_count=len(layers[i]),missing_count=len(missing),
                    stationary_witness_missing=(F(-8),F(0)) in missing))
                snapshots.append(copy.deepcopy(history))
            item=dict(case=name,variant=variant,missing_at_3=steps[6]['missing_count'],
                missing_at_4=steps[8]['missing_count'],reference_at_4=len(layers[8]),
                witness_missing=steps[8]['stationary_witness_missing'],admissions=len(applied),
                terminal_shadows=len(history),terminated=True)
            if representation!='base':item['semantic_input_equivalence']='superset plus exact copy or contained interval with same inbound/history; full union unchanged'
            summary.append(item);print(json.dumps(item),flush=True)
            (OUT/(name+'__'+variant+'.json')).write_text(json.dumps(dict(summary=item,steps=steps,reference=reference),indent=2)+'\n')
            all_runs[(name,variant)]=snapshots
        finally:ShadowUtils._update_shadow=original
    (OUT/(name+'__visibility.json')).write_text(json.dumps(sample_rows,indent=2)+'\n')

# Analytic continuous witness, in addition to finite exhaustive reachability.
fields=all_reference['pipeline_two_lanes']['fields'];layers=all_reference['pipeline_two_lanes']['layers']
stationary=[dict(t=t,q=-8,v=0,a=0,footprint_ds=[8,11],visibility_clearance_m=float(clearance((F(-8),F(0)),fields[t]))) for t in times]
assert all(x['visibility_clearance_m']>0 for x in stationary)
assert (F(-8),F(0)) in layers[-1]
w=dict(trajectory=stationary,continuous_certificate='q(t)=-8, v(t)=0, a(t)=0 on [0,4]; body ds in [8,11]; all prescribed FOV fields leave this interval hidden',
      grid_witness=witness(layers,times,(F(-8),F(0)),8),
      full_impl_union='No shadow remains at t=4 in original connected case; no alternative shadow can cover the witness',
      obstacle_constraints='Closed two-lane abstract road; no known obstacles; body entirely inside lane 1; no lateral dynamics')
(OUT/'witness.json').write_text(json.dumps(w,indent=2)+'\n')
(OUT/'reference.pkl').write_bytes(pickle.dumps(all_reference,protocol=4))
(OUT/'implementation_states.pkl').write_bytes(pickle.dumps(all_runs,protocol=4))
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
files=list(Path(__file__).resolve().parent.glob('*.py'))
for f in files:(OUT/f.name).write_bytes(f.read_bytes())
(OUT/'manifest.json').write_text(json.dumps(dict(command=sys.argv,seed=0,device='CPU',status='completed',termination='all bounded cases terminated',
    source={str(f.relative_to(ROOT)):sha(f) for f in files},inputs_sha256=sha(OUT/'inputs.json'),
    commit='2b6b06637850b406cfbeab926a3dedc01edad91e',
    generated_interventions={f.name:sha(f) for f in OUT.glob('*shadow*.py')},
    timestamp=datetime.datetime.utcnow().isoformat()+'Z'),indent=2)+'\n')
