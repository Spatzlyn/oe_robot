#!/usr/bin/env python3
import datetime,hashlib,json,sys,traceback
from pathlib import Path
from types import SimpleNamespace as NS
import os
HERE=Path(os.environ['OE_OUTPUT'])
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_native_search as base
from risk_analysis.shadow_utils import ShadowUtils
import carla

def main():
    results=[]
    old_create=ShadowUtils.create_shadow
    old_repeat=ShadowUtils._check_repeated_bwd_shadow
    for name in ['D_template_000','D_template_012']:
        archived=json.loads((Path(__file__).resolve().parents[2]/'fixtures/pruning/development'/(name+'.json')).read_text())
        m=base.setup();lane=m.road_network.find_lane_id(100);lane.lane_section=NS(s_start=0.)
        waypoint=NS(road_id=100,section_id=0,lane_id=1,s=20.)
        m.client=NS(ego=NS(get_location=lambda:carla.Location(x=20.,y=0.,z=0.)),
                    map=NS(get_waypoint=lambda *args,**kwargs:waypoint))
        def find_lane(road,section,laneid):
            assert (road,section,laneid)==(100,0,1)
            return lane
        m.road_network.find_lane=find_lane
        generated=[];subsets=[];active_t=[0.]
        def create(self,*args,**kwargs):
            sh=old_create(self,*args,**kwargs)
            generated.append(dict(t=active_t[0],args=list(args),shadow=base.compact(sh)))
            return sh
        def repeated(self,sh,retained):
            rejected=old_repeat(self,sh,retained)
            subset=[r for ds,r in retained if ds==sh.root.ds_out and base.signature(r)<base.signature(sh)]
            if rejected and subset:
                subsets.append(dict(t=active_t[0],candidate=base.compact(sh),retained_strict_subsets=base.forest(subset)))
            return rejected
        ShadowUtils.create_shadow=create;ShadowUtils._check_repeated_bwd_shadow=repeated
        row=dict(case=name,status='started',epochs=[],native_constructor_calls=generated,native_subset_events=subsets)
        try:
            for i,t in enumerate([0.,.25,.5,.75,1.]):
                active_t[0]=t
                vis=base.fields(archived['schedule'],i)
                m.vis_checker_depth=NS(check_visibility=vis)
                for laneid in [2,3]:
                    assert all(not vis(m.road_network.find_lane_id(laneid),ds) for ds in [7.5,8,8.5,9,9.5,10,10.5,11,11.5])
                maps,history=m.update_visibility(None,None,t)
                observed=base.forest(history);membership,ambiguous=base.support(history,m)
                row['epochs'].append(dict(t=t,forest=observed,witness_membership=membership,implicit_uncertainty=ambiguous,
                                         all_post_update_fields_equal_archived=observed==archived['epochs'][i]['final_forest']))
            row.update(status='completed',native_wrapper_updates=5,
                       legal_ego_waypoint=0<=waypoint.s-lane.lane_section.s_start<=lane.length,
                       native_initial_inbound_ds=generated[0]['shadow']['root']['ds_in'],
                       all_post_update_parity=all(e['all_post_update_fields_equal_archived'] for e in row['epochs']))
        except Exception as exc:
            row.update(status='invalid',error=repr(exc),traceback=traceback.format_exc())
        finally:
            ShadowUtils.create_shadow=old_create;ShadowUtils._check_repeated_bwd_shadow=old_repeat
        base.dump(HERE/(name+'.json'),row);results.append(row)
    summary=[{k:v for k,v in r.items() if k not in ['epochs','native_constructor_calls','native_subset_events']} for r in results]
    base.dump(HERE/'summary.json',summary)
    base.dump(HERE/'manifest.json',dict(command=sys.argv,device='CPU',conditions=2,native_wrapper_updates=sum(x.get('native_wrapper_updates',0) for x in results),protocol_sha256=hashlib.sha256((HERE/'protocol.json').read_bytes()).hexdigest(),harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
