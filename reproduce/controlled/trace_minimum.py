#!/usr/bin/env python3
"""Expose whether the job that occupies a key produced surviving coverage."""
import argparse,copy,datetime,json,queue,sys
from pathlib import Path
from small_graph import manager,flat_shadow,field
from common import ROOT,sha,compact,instrument_update
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.shadow import OutBound

ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
out=args.output.resolve();out.mkdir(exist_ok=False)
m=manager();old,traced,records,source=instrument_update();original_primitive=m._update_bwd_shadow
def primitive(shadow,*args):
    before=compact(shadow);value=original_primitive(shadow,*args)
    mature,children,visited=value
    records.append(dict(stage='primitive_return',t=args[-1],input=before,
        mature=None if mature is None else compact(mature),children=[compact(x) for x in children],visited=visited))
    return value
m._update_bwd_shadow=primitive;history=[];steps=[];ShadowUtils._update_shadow=traced
try:
    for i in range(9):
        t=i/2
        if i==0:
            s=flat_shadow();s.root=OutBound(1,0,0);s.leaf_list=[];s.leaf_depth=[];work=[s]
        else:work=m.predict_shadow(history,t)
        q=queue.Queue()
        for s in work:q.put(s)
        input_snapshot=[compact(s) for s in work]
        maps,history=m._update_shadow(q,field,None,None,t)
        steps.append(dict(t=t,initial_work=input_snapshot,final=[compact(s) for s in history]))
finally:ShadowUtils._update_shadow=old
empty=[r for r in records if r['stage']=='primitive_return' and r['t']==3 and r['input']['root'].get('ds_out')==2 and r['input']['root'].get('ds_in')==2.5]
assert len(empty)==1 and empty[0]['mature'] is None
rejected=[r for r in records if r['stage']=='admission_test' and r['t']==3 and r['rejected']]
assert any(r['shadow']['root'].get('ds_in')==15 and r['shadow']['root'].get('ds_out')==2 for r in rejected)
(out/'events.json').write_text(json.dumps(records,indent=2)+'\n')
(out/'steps.json').write_text(json.dumps(steps,indent=2)+'\n')
(out/'summary.json').write_text(json.dumps(dict(key=[1,2],first_job_input_interval=[2,2.5],first_job_mature_output=None,
    rejected_input_interval=[2,15],interpretation='A searched key persists even when its earlier job leaves no mature coverage.',
    non_nested_intervals_necessary=False),indent=2)+'\n')
(out/'source_executed.py').write_bytes(Path(__file__).read_bytes());(out/'instrumented_update.py').write_text(source)
(out/'manifest.json').write_text(json.dumps(dict(command=sys.argv,seed=0,device='CPU',status='completed',termination='nine finite updates; key occupant returned no mature shadow',source_sha256=sha(__file__),timestamp=datetime.datetime.utcnow().isoformat()+'Z'),indent=2)+'\n')
print((out/'summary.json').read_text())
