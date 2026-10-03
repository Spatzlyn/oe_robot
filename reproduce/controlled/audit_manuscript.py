#!/usr/bin/env python3
"""Bounded CPU audits for the manuscript; no simulator or propagation edits."""
import argparse, datetime, inspect, json, pickle, subprocess, sys
from pathlib import Path
from fractions import Fraction as F
import planning
from shapely.geometry import Point, LineString, shape
from shapely.affinity import translate
from common import ROOT, sha, compact
from small_graph import manager, field
from reference import field_intervals, hidden, transition
from risk_analysis.reachable_set import translate_polygon

ap=argparse.ArgumentParser()
for name in ['small-run','control-run','action-run','far-run','trace-run','output']:
    ap.add_argument('--'+name,type=Path,required=True)
ap.add_argument('--include-ancillary',action='store_true',help='Also reproduce the separate velocity-envelope diagnostic')
args=ap.parse_args();out=args.output.resolve();out.mkdir(exist_ok=False)
used={}
def read(path,binary=False):
    path=path.resolve();used[str(path.relative_to(ROOT)) if ROOT in path.parents else str(path.parent.name+'/'+path.name)]=sha(path)
    return pickle.loads(path.read_bytes()) if binary else json.loads(path.read_text())
def save(name,data):
    (out/name).write_text(json.dumps(data,indent=2)+'\n')

refs=read(args.small_run/'reference.pkl',True)
states=read(args.small_run/'implementation_states.pkl',True)
base=refs['pipeline_two_lanes'];m=manager()
samples={}
for lane in m.road_network.id_map.values():
    for ds in lane.waypoint_ds:
        q=-ds if lane.lanelet_id==1 else 10-ds
        samples[F(str(q))]=bool(field(lane,ds,None,None,2.5))
base_vis=field_intervals(samples.items());filled=dict(samples);filled[F(-2)]=True
fill_vis=field_intervals(filled.items())
control=read(args.control_run/'fill_one_query__original.json')
assert base_vis==base['fields'][2.5]
assert fill_vis==[tuple(F(x) for x in ab) for ab in control['fields']['2.5']]
assert all([tuple(F(x) for x in ab) for ab in control['fields'][str(t)]]==base['fields'][t]
           for t in base['times'] if t!=2.5)
def hidden_components(visible):
    return [(a[1],b[0]) for a,b in zip(visible,visible[1:]) if a[1]<b[0]]
def erode_front(components,length=F(3)):
    return [(a+length,b) for a,b in components if b-a>length]
bh,fh=hidden_components(base_vis),hidden_components(fill_vis)
assert bh==[(F('-14.75'),F('-3.25')),(F('-2.25'),F('-1.75'))]
assert fh==bh[:1] and erode_front(bh)==erode_front(fh)==[(F('-11.75'),F('-3.25'))]
boundary=[]
for q in [F('-11.75'),F('-11.75')+F(1,1000000),F('-3.25')-F(1,1000000),F('-3.25')]:
    a=hidden((q,F(0)),base_vis);b=hidden((q,F(0)),fill_vis)
    assert a==b
    boundary.append(dict(q=str(q),base_hidden=a,fill_hidden=b))
save('observation_equivalence.json',dict(
    base_visible=[[str(a),str(b)] for a,b in base_vis],fill_visible=[[str(a),str(b)] for a,b in fill_vis],
    base_hidden_open=[[str(a),str(b)] for a,b in bh],fill_hidden_open=[[str(a),str(b)] for a,b in fh],
    admissible_front_open=[[str(a),str(b)] for a,b in erode_front(bh)],boundary_checks=boundary,
    other_observation_fields_equal=True,footprint_length=3,
    conclusion='Analytic equality of continuous hidden-state and feasible-trajectory sets in the specified 1D observation model; interval erosion proof is in docs/shadow_semantics.md.'))

if args.include_ancillary:
    # Native FRS audit using the frozen t=1 shadow, without modifying its bound.
    s=states[('pipeline_two_lanes','original')][2][0]
    assert (s.root.ds_in,s.root.ds_out,s.leaf_depth)==(15,3,[12])
    prefix=[(F('-11.5'),F(6)),(F(-8),F(8)),(F('-3.5'),F(10))]
    assert all(transition(a,4)==b for a,b in zip(prefix,prefix[1:]))
    assert all(hidden(st,base['fields'][t]) for st,t in zip(prefix,[0,.5,1]))
    rows=[]
    for n in [20,200,2000]:
        g=m.bwd_shadow_FRS(s,1,1,n=n)
        for convention,offset in [('front',0),('center',-1.5),('rear',-3)]:
            x=-3.5+offset+s.root.ds_out
            line=g.intersection(LineString([(x,0),(x,30)]))
            vmax=max(y for _,y in line.coords)
            # Native checker translation is horizontal: x -> x - p_rel.
            p_rel=s.root.ds_out+8.379379539499421
            translated=translate_polygon(g,-p_rel)
            before=g.covers(Point(x,10));after=translated.covers(Point(x-p_rel,10))
            assert before==after==False
            rows.append(dict(n=n,coordinate_interpretation=convention,local_x=x,checker_x=x-p_rel,
                             bound_at_x=vmax,global_polygon_max_v=g.bounds[3],covered=before,translated_covered=after))
    cap=m.calc_V_max(s.root,9,1)
    assert abs(cap-(97**.5))<1e-12
    assert all(abs(row['global_polygon_max_v']-cap)<1e-12 for row in rows)
    # Normal-control prefix is the same native input; it also has this discrepancy.
    normal=read(args.control_run/'normal_duplicate__original.json')['steps'][2]
    assert normal['shadows']==[compact(s)]
    stationary=[]
    for v in ['original','single_admission','mature_coverage_guard']:
        for t,forest in zip(base['times'],states[('pipeline_two_lanes',v)]):
            present=any(sh.root.id==1 and m.bwd_shadow_FRS(sh,t,t).buffer(1e-9).covers(Point(-8+sh.root.ds_out,0)) for sh in forest)
            stationary.append(dict(variant=v,t=t,native_position_speed_covered=present,whole_forest_count=len(forest)))
    save('velocity_audit.json',dict(classification='native_bound_footprint_discrepancy_in_stated_1D_model',
        source_shadow=compact(s),path=[dict(t=t,q=float(q),v=float(v)) for t,(q,v) in zip([0,.5,1],prefix)],
        native_cap=cap,native_algebra='Vin=(9 - 0.5*8*1^2)/1=5; Vout=sqrt(5^2+2*4*9)=sqrt(97)',
        actual_travel=8,available_front_travel=9,rows=rows,normal_control_same_prefix=True,
        convention_scope='Shadow boundaries are visibility geometry, not centers. Native shadow FRS is a longitudinal occupancy/boundary envelope without a unique front/rear label; all three physical markers exceed its global velocity cap. Horizontal translation cannot alter this conclusion.',
        no_native_change=True,stationary=stationary))

# Reuse stored geometry: no live checker/episode rerun. Remove the background
# conceptually only after verifying it is disjoint from every recorded zone.
near=read(args.action_run/'results.json');far=read(args.far_run/'results.json')
allowed={v:[i for i,c in enumerate(a['checks']) if c['result'][0]] for v,a in near.items()}
assert all(allowed[v]==[1,6,7,12] for v in allowed if v!='original')
future={transition(state,a) for state in base['layers'][-1] for a in [-8,-4,0,4]}
assert len(future)==451
background=[];components=[]
for metric in near['reference']['metrics']:
    if metric.get('lane')!=135 or 'FRS' not in metric:continue
    g=shape(metric['FRS']);z=shape(metric['danger_zone'])
    assert g.disjoint(z)==metric['disjoint']
    if g.geom_type=='Polygon':
        assert g.disjoint(z)
        background.append(dict(action=metric['action'],disjoint=True))
    else:
        assert g.geom_type=='MultiPoint' and len(g.geoms)==len(future)
        shift=min(p.x for p in g.geoms)-float(min(q for q,v in future))
        expected={(round(float(q)+shift,10),float(v)) for q,v in future}
        assert {(round(p.x,10),p.y) for p in g.geoms}==expected
        shifted=translate(g,xoff=-100)
        fm=[r for r in far['reference']['metrics'] if r.get('lane')==135 and r.get('FRS',{}).get('type')=='MultiPoint'
            and r['action']==metric['action'] and shape(r['danger_zone']).equals(z)]
        assert len(fm)==1 and shifted.hausdorff_distance(shape(fm[0]['FRS']))<1e-10
        assert shifted.disjoint(z) and fm[0]['disjoint']
        components.append(dict(action=metric['action'],near_disjoint=g.disjoint(z),far_disjoint=True,
            shift_m=shift,point_count=len(g.geoms),far_translation_m=-100))
assert len(background)==len(components)==32
save('geometry_audit.json',dict(allowed_action_ids=allowed,background=background,components=components,
    reachable_count=len(future),background_removed_in_far=True,
    interpretation='Stored native intersection geometries only; not a new checker-harness or simulator run. Background cannot account for the observed near/far intersection difference in these 32 calls.'))
trace=read(args.trace_run/'summary.json')
assert trace['first_job_mature_output'] is None
for name,fn in [('calc_V_max',m.calc_V_max),('bwd_shadow_FRS',m.bwd_shadow_FRS),('translate_polygon',translate_polygon)]:
    (out/(name+'.py')).write_text(inspect.getsource(fn))
(out/'source_executed.py').write_bytes(Path(__file__).read_bytes())
save('manifest.json',dict(command=sys.argv,seed=0,device='CPU',status='completed',
    termination='observation and stored-geometry audits completed; optional velocity audit recorded separately',
    commit='2b6b06637850b406cfbeab926a3dedc01edad91e',
    source_sha256=sha(__file__),input_hashes=used,timestamp=datetime.datetime.utcnow().isoformat()+'Z',
    scope='Existing discovery artifacts plus direct native-function CPU audit; no independent scene, simulator rollout, or full checker-harness rerun.'))
print(json.dumps(dict(status='completed',observation_sets_analytically_equal=True,velocity_classification='separate native bound discrepancy in stated model' if args.include_ancillary else 'not_run_ancillary',geometry_checks=len(components))))
