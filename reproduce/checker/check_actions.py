#!/usr/bin/env python3
"""Unmodified native checker with either shadow FRS or exact finite reference FRS.

The small lane is embedded at lane 135 coordinates in the logged intersection
checker context. This is a CPU checker fixture, not a new simulator rollout.
"""
import argparse,copy,datetime,heapq,json,pickle,subprocess,sys
from pathlib import Path
from fractions import Fraction as F
from shapely.geometry import MultiPoint
import planning
from common import ROOT,sha
from reference import transition,witness
from rss_checkpoint import restore
from rss_mechanism_diagnostics import apply_context,evaluate_actions

class FiniteSet(MultiPoint):
    # Native checker consumes an exterior coordinate envelope only for maxima.
    # disjoint/intersection remain EXACT MultiPoint set operations, no hull.
    @property
    def exterior(self):return self
    @property
    def xy(self):return ([p.x for p in self.geoms],[p.y for p in self.geoms])

ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--small-run',type=Path,default=ROOT/'fixtures/controlled')
ap.add_argument('--map',type=Path,required=True);ap.add_argument('--offset',type=float,default=0.);ap.add_argument('--isolate-lane',action='store_true');args=ap.parse_args()
OUT=args.output.resolve();OUT.mkdir(exist_ok=False)
pairfile=ROOT/'fixtures/checker/pair_566.pkl'
pair=pickle.loads(pairfile.read_bytes())
checkpoint=ROOT/'fixtures/checker/cycle_0005.pkl'
p,root=restore(checkpoint,args.map)
from risk_analysis.shadow import Shadow,OutBound
from risk_analysis.shadow_utils import ShadowUtils
small=args.small_run.resolve()
refs=pickle.loads((small/'reference.pkl').read_bytes())['pipeline_two_lanes']
states=pickle.loads((small/'implementation_states.pkl').read_bytes())
original=ShadowUtils.bwd_shadow_FRS;reference_records=[]

def finite_frs(manager,shadow,t_sense,t_predict,*args,**kwargs):
    if shadow.parent_id!='independent_finite_reference':return original(manager,shadow,t_sense,t_predict,*args,**kwargs)
    assert t_sense==4 and t_predict==4.5,(t_sense,t_predict)
    points={};dt=F(str(t_predict))-F(str(t_sense))
    for state in refs['layers'][-1]:
        for a in [-8,-4,0,4]:
            nxt=transition(state,a,dt)
            points.setdefault(nxt,(state,a))
    geom=FiniteSet([(float(q),float(v)) for q,v in points])
    reference_records.append(dict(t_sense=t_sense,t_predict=t_predict,count=len(points),
        q_min=float(min(q for q,v in points)),q_max=float(max(q for q,v in points)),
        v_min=float(min(v for q,v in points)),v_max=float(max(v for q,v in points))))
    return geom

results={};summary=[]
for variant in ['original','single_admission','reference','mature_coverage_guard','structural_key']:
    apply_context(p,pair['contexts']['predicted_B'])
    maps=copy.deepcopy(pair['cases']['predicted_B']['shadow_map'])
    if args.isolate_lane:maps.pop(135,None)
    if variant=='reference':
        s=Shadow();s.risk_bound=False;s.parent_id='independent_finite_reference';s.root=OutBound(135,args.offset,4)
        s.leaf_list=[s.root];s.leaf_depth=[None];add=[s]
    else:
        add=copy.deepcopy(states[('pipeline_two_lanes',variant)][-1])
        for s in add:
            assert s.root.id==1 and not s.root.child_node
            s.root.id=135;s.parent_id=215
            s.root.ds_in+=args.offset;s.root.ds_out+=args.offset
    for s in add:heapq.heappush(maps.setdefault(s.root.id,[]),(s.root.ds_out,s))
    ShadowUtils.bwd_shadow_FRS=finite_frs
    try:result=evaluate_actions(p,maps,pair['actions'])
    finally:ShadowUtils.bwd_shadow_FRS=original
    results[variant]=result
    summary.append(dict(variant=variant,safe_count=sum(c['result'][0] for c in result['checks'])))
    print(json.dumps(summary[-1]),flush=True)

original_allowed={i for i,c in enumerate(results['original']['checks']) if c['result'][0]}
reference_allowed={i for i,c in enumerate(results['reference']['checks']) if c['result'][0]}
comparison=dict(summary=summary,additional_allowed_vs_reference=sorted(original_allowed-reference_allowed),
    longitudinal_offset_m=args.offset,background_lane135_removed=args.isolate_lane,
    interpretation='Reference is an exact finite underapproximation, not a universal safety oracle. Rejections use reachable samples in original danger zones, not proof of unavoidable collision.',
    context='Small-graph shadow/reference state transplanted into fixed D05 intersection checker context; all candidate values/checker functions unchanged',
    reference_frs_calls=reference_records)
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
(OUT/'summary.json').write_text(json.dumps(comparison,indent=2)+'\n')
(OUT/'manifest.json').write_text(json.dumps(dict(command=sys.argv,seed=0,device='CPU',status='completed',termination='all fixed 18-action grids evaluated',
    source={str(Path(__file__).resolve().relative_to(ROOT)):sha(__file__)},map_sha256=sha(args.map),inputs={str(f.relative_to(ROOT)) if ROOT in f.parents else f.name:sha(f) for f in [pairfile,checkpoint,small/'reference.pkl',small/'implementation_states.pkl']},
    commit='2b6b06637850b406cfbeab926a3dedc01edad91e',timestamp=datetime.datetime.utcnow().isoformat()+'Z'),indent=2)+'\n')
(OUT/'source_executed.py').write_bytes(Path(__file__).read_bytes())
