#!/usr/bin/env python3
"""Bounded semantic checks, reduction-site ablations, and reachable risk witnesses."""
import argparse,copy,datetime,json,pickle,queue,subprocess,sys
from pathlib import Path
from fractions import Fraction as F
import planning
import numpy as np
from shapely.geometry import Point,LineString,shape
from common import ROOT,sha,compact,position_segments,covers_position,instrument_update
from small_graph import manager,flat_shadow,field,Lane,Network
from reference import field_intervals,propagate,witness,transition,hidden,clearance
from conservative_reduction import make,dominates
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.shadow import OutBound

ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--small-run',type=Path,default=ROOT/'fixtures/controlled');args=ap.parse_args()
OUT=args.output.resolve();OUT.mkdir(exist_ok=False)
small=args.small_run.resolve()
refs=pickle.loads((small/'reference.pkl').read_bytes());runs=pickle.loads((small/'implementation_states.pkl').read_bytes())
original=ShadowUtils._update_shadow
configuration=dict(seed=0,device='CPU',experiments=['full position-speed FRS coverage','single-site correction ablations',
    'one visibility query filled','normal duplicate without island','different two-lane lengths and occlusion extent',
    'same geometry/different observation history unit control','native danger-zone witness'],
    interpretation='Designed controls and discovery checks, not independent scene samples or population rates')
(OUT/'protocol.json').write_text(json.dumps(configuration,indent=2)+'\n')
coverage=[]
for case,data in refs.items():
    m=manager()
    for variant in ['original','single_admission','mature_coverage_guard']:
        for i,(layer,shadows) in enumerate(zip(data['layers'],runs[(case,variant)])):
            t=data['times'][i]
            geoms=[(s.root.ds_out,m.bwd_shadow_FRS(s,t,t)) for s in shadows if s.root.id==1]
            missing=[]
            for q,v in layer:
                if not any(g is not None and g.buffer(1e-9).covers(Point(float(q)+ds,float(v))) for ds,g in geoms):
                    missing.append([str(q),str(v)])
            coverage.append(dict(case=case,variant=variant,t=t,reference_count=len(layer),missing_count=len(missing),missing=missing))
(OUT/'full_state_coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

times=refs['pipeline_two_lanes']['times'];base_fields=refs['pipeline_two_lanes']['fields']
def fixture(name,mode):
    m=manager()
    if name=='different_lengths':m.road_network=Network([Lane(1,16,successor=[2]),Lane(2,6,predecessor=[1])])
    def vis(lane,ds,data,pose,t):
        if name=='fill_one_query' and lane.lanelet_id==1 and t==2.5 and ds==2:return True
        if name=='normal_duplicate' and lane.lanelet_id==1 and t in [2.5,3]:return ds<=3 or ds>=15
        if name=='different_lengths' and lane.lanelet_id==1 and ds>=12:return True
        return field(lane,ds,data,pose,t)
    fields={}
    for t in times:
        samples={}
        for lane in m.road_network.id_map.values():
            for ds in lane.waypoint_ds:
                q=-ds if lane.lanelet_id==1 else lane.length-ds
                samples[q]=bool(vis(lane,ds,None,None,t))
        fields[t]=field_intervals(samples.items(),domain=(-m.road_network.id_map[1].length,m.road_network.id_map[2].length))
    initial=[(F(i,4),F(v)) for i in range(-48,-15) for v in range(16)]
    layers=propagate(initial,times,fields)
    settings={'original':(False,False,False),'admission_only':(True,False,False),
              'visited_only':(False,True,False),'mature_only':(False,False,True),'all_guarded':(True,True,True)}
    fn,code=make(original,*settings[mode]);ShadowUtils._update_shadow=fn
    history=[];steps=[]
    try:
        for i,t in enumerate(times):
            if t==0:
                s=flat_shadow();s.root=OutBound(1,0,0);s.leaf_list=[];s.leaf_depth=[];work=[s]
            else:work=m.predict_shadow(history,t)
            if name=='normal_duplicate' and t==2.5:work+=copy.deepcopy(work)
            q=queue.Queue()
            for s in work:q.put(s)
            maps,history=m._update_shadow(q,vis,None,None,t)
            segments=position_segments(history,m.road_network)
            missed=[s for s in layers[i] if not covers_position(segments,1,float(-s[0]))]
            steps.append(dict(t=t,shadows=[compact(s) for s in history],reference_count=len(layers[i]),position_missing=len(missed)))
    finally:ShadowUtils._update_shadow=original
    item=dict(fixture=name,mode=mode,reference_at_4=len(layers[-1]),missing_at_4=steps[-1]['position_missing'],
        final_shadows=len(history),same_finite_reference_as_base=all(set(a)==set(b) for a,b in zip(layers,refs['pipeline_two_lanes']['layers'])),
        scope='same finite sets does not prove continuous-set equality',terminated=True)
    (OUT/(name+'__'+mode+'.json')).write_text(json.dumps(dict(summary=item,steps=steps,fields={str(t):[[str(a),str(b)] for a,b in f] for t,f in fields.items()}),indent=2)+'\n')
    return item

ablations=[fixture('base',mode) for mode in ['original','admission_only','visited_only','mature_only','all_guarded']]
controls=[fixture(case,mode) for case in ['fill_one_query','normal_duplicate','different_lengths'] for mode in ['original','admission_only','all_guarded']]

# History matters even when position/extent match. This is a constructed unit
# input, not an independently recorded physical episode.
m=manager();old=flat_shadow(t=3,t_in=0);fresh=flat_shadow(t=3,t_in=3)
history_test=dict(position_intervals_equal=True,old_history_bound=m.calc_V_max(old.root,9,3),
    fresh_history_bound=m.calc_V_max(fresh.root,9,3),
    original_mature_discards_fresh=m._check_repeated_bwd_shadow(fresh,[(old.root.ds_out,old)]),
    guard_discards_fresh=dominates(old,fresh),
    scope='constructed same-geometry history unit test; not a second pipeline counterexample')

# Witnesses for both native danger zones of the same action.
action=[173,-.25,15,0,4,4.5]
data=json.loads((ROOT/'fixtures/audit/near/results.json').read_text())['reference']
metrics=[m for m in data['metrics'] if m['action']==action and m.get('lane')==135 and m.get('disjoint') is False]
base=refs['pipeline_two_lanes'];future={}
for state in base['layers'][-1]:
    for a in [-8,-4,0,4]:future.setdefault(transition(state,a),(state,a))
risk_witnesses=[]
for metric in metrics:
    pts=metric['FRS']['coordinates'];shift=min(p[0] for p in pts)-float(min(s[0] for s in future))
    zone=shape(metric['danger_zone'])
    candidates=[]
    for end,(start,a) in future.items():
        pt=Point(float(end[0])+shift,float(end[1]))
        if zone.contains(pt):candidates.append((zone.boundary.distance(pt),end,start,a))
    margin,end,start,a=max(candidates)
    path=witness(base['layers'],times,start,len(times)-1)
    # Verify recorded prefix algebra and full footprint at every observation.
    for left,right in zip(path,path[1:]):
        st=(F(left['q_exact']),F(left['v_exact']));expected=transition(st,right['previous_acceleration'])
        assert expected==(F(right['q_exact']),F(right['v_exact']))
    assert all(hidden((F(row['q_exact']),F(row['v_exact'])),base_fields[row['t']]) for row in path)
    path.append(dict(t=4.5,q=float(end[0]),v=float(end[1]),q_exact=str(end[0]),v_exact=str(end[1]),previous_acceleration=a))
    risk_witnesses.append(dict(path=path,checker_coordinate=[float(end[0])+shift,float(end[1])],coordinate_shift=shift,
        raw_mixed_coordinate_margin=float(margin),margin_warning='Not a physical safety distance',
        exact_point_in_danger=True,observation_scope='hidden through t=4; subsequent FRS propagation has no extra observation, matching checker',
        collision_claim=False))

# Keep the separate prefix envelope discrepancy instead of hiding it.
prefix_state=(F(-7,2),F(10));prefix_path=witness(base['layers'],times,prefix_state,2)
s=runs[('pipeline_two_lanes','mature_coverage_guard')][2][0]
g=manager().bwd_shadow_FRS(s,1,1);x=float(prefix_state[0])+s.root.ds_out
cross=g.intersection(LineString([(x,0),(x,30)]))
native_max=max(y for xx,y in cross.coords)
prefix=dict(path=prefix_path,reference_state=[float(x) for x in prefix_state],native_max_speed_at_same_position=native_max,
    speed_gap=10-native_max,scope='Separate zero-horizon native FRS envelope discrepancy before queue failure; not fixed by admission correction; continuous interpretation still requires footprint/FRS convention audit')

summary=dict(ablations=ablations,controls=controls,history_unit_test=history_test,
    main_target_epoch_full_state_missing={v:sum(x['missing_count'] for x in coverage if x['case']=='pipeline_two_lanes' and x['variant']==v and x['t']>=2) for v in ['original','single_admission','mature_coverage_guard']},
    prefix_discrepancy=prefix,risk_witnesses=risk_witnesses)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for f in Path(__file__).resolve().parent.glob('*.py'):(OUT/f.name).write_bytes(f.read_bytes())
(OUT/'manifest.json').write_text(json.dumps(dict(command=sys.argv,seed=0,device='CPU',status='completed',termination='bounded controls and witness checks completed',
    source={f.name:sha(f) for f in OUT.glob('*.py')},input_hashes={str(f.relative_to(ROOT)) if ROOT in f.parents else f.name:sha(f) for f in [small/'reference.pkl',small/'implementation_states.pkl',ROOT/'fixtures/audit/near/results.json']},
    timestamp=datetime.datetime.utcnow().isoformat()+'Z'),indent=2)+'\n')
print(json.dumps(dict(ablations=ablations,controls=controls,history=history_test,prefix_speed_gap=prefix['speed_gap']),indent=2))
