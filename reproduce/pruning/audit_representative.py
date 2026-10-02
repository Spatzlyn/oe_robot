#!/usr/bin/env python3
import datetime,hashlib,inspect,json,sys,textwrap
from pathlib import Path
import run_native_search as base

import os
HERE=Path(os.environ['OE_OUTPUT'])
CASE=json.loads((Path(__file__).resolve().parents[2]/'fixtures/pruning/development/D_template_000.json').read_text())
SOURCE=textwrap.dedent(inspect.getsource(base.ORIGINAL))
TARGET=.25
VARIANTS={
    'original_v2_trace':SOURCE,
    'admission_only_off_at_target':SOURCE.replace('if new_shadow_begin not in bwd_searched_begin:', 'if t == .25 or new_shadow_begin not in bwd_searched_begin:'),
    'visited_only_off_at_target':SOURCE.replace('if bound_lane_id in bwd_visited_lane:', 'if t != .25 and bound_lane_id in bwd_visited_lane:'),
    'mature_only_off_at_target':SOURCE.replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)','return False if t == .25 else self._check_repeated_bwd_shadow(shadow2check, shadow_list)')}

def main():
    out=HERE/'representative_attribution';out.mkdir(exist_ok=False);rows=[]
    for name,source in VARIANTS.items():
        hook=[]
        def emit(stage,t,shadow,native_reject):
            hook.append(dict(stage=stage,t=t,shadow=base.compact(shadow),native_condition_reject=bool(native_reject)))
        # Only record native decision inputs; chosen research intervention remains explicit.
        lines=[]
        for line in source.splitlines():
            if 'if ' in line and 'bound_lane_id in bwd_visited_lane:' in line:
                indent=line[:len(line)-len(line.lstrip())]
                lines.append(indent+"_audit_hooks('visited_test',t,cur_shadow,bound_lane_id in bwd_visited_lane)")
            if 'if ' in line and 'new_shadow_begin not in bwd_searched_begin:' in line:
                indent=line[:len(line)-len(line.lstrip())]
                lines.append(indent+"_audit_hooks('admission_test',t,new_shadow,new_shadow_begin in bwd_searched_begin)")
            lines.append(line)
        traced='\n'.join(lines)+'\n';(out/(name+'.py')).write_text(traced)
        base.SOURCE=traced;base.ORIGINAL.__globals__['_audit_hooks']=emit
        result=base.run_case(dict(id=CASE['case'],schedule=CASE['schedule']))
        result['reduction_site_events']=hook;result['variant']=name
        result['prior_epoch_matches_archived']=result['epochs'][0]['final_forest']==CASE['epochs'][0]['final_forest']
        result['target_input_matches_archived']=result['epochs'][1]['predicted_input']==CASE['epochs'][1]['predicted_input']
        if name=='original_v2_trace':result['all_epochs_match_archived']=all(x['final_forest']==y['final_forest'] for x,y in zip(result['epochs'],CASE['epochs']))
        base.dump(out/(name+'.json'),result)
        rows.append(dict(variant=name,status=result['status'],prior_epoch_matches=result['prior_epoch_matches_archived'],target_input_matches=result['target_input_matches_archived'],target_witness_membership=result['epochs'][1]['witness_membership'],all_epochs_match_archived=result.get('all_epochs_match_archived')))
    base.SOURCE=SOURCE;base.ORIGINAL.__globals__.pop('_audit_hooks',None)
    base.dump(out/'summary.json',rows)
    base.dump(out/'manifest.json',dict(command=sys.argv,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),protocol_sha256=hashlib.sha256((HERE/'representative_attribution_protocol.json').read_bytes()).hexdigest(),finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=len(rows),device='CPU'))
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
