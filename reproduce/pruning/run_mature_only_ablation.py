#!/usr/bin/env python3
"""D1 causal follow-up: disable exactly mature backward reduction, other rules unchanged."""
import datetime,json
from pathlib import Path
from run_boundaries import methods,compile_code,run_case,digest,ROOT,HERE
import subprocess,sys
out=HERE/'mature_only_ablation';out.mkdir(exist_ok=False)
original,codes,fns=methods()
base=codes['original']
target='return self._check_repeated_bwd_shadow(shadow2check, shadow_list)'
assert base.count(target)==1
code=base.replace(target,'return False  # only backward mature duplicate reduction disabled')
(out/'mature_only_off.py').write_text(code)
protocol=json.loads((HERE/'protocol.json').read_text());case=protocol['development'][0]
freeze=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),role='development causal follow-up; not extra heldout condition',question='Does disabling exactly the mature-output predicate recover the stationary branch witness while admission/visited remain native?',case=case,baseline='../development/D1_subset_fork__original.json',prediction='witness restored',changes='one native mature-return predicate only',harness_sha256=digest(Path(__file__).with_name('run_boundaries.py')),intervention_sha256=digest(out/'mature_only_off.py'),no_validation_rule_changes=True)
(out/'protocol.json').write_text(json.dumps(freeze,indent=2)+'\n')
fn=compile_code(code,original)
row=run_case(case,'mature_only_off',code,original,fn,out)
(out/'manifest.json').write_text(json.dumps(dict(command=sys.argv,source_revision='2b6b06637850b406cfbeab926a3dedc01edad91e',cpu_only=True,attempts=1,parity_execution_calls=1,result_status=row['status'],completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),harness_sha256=digest(__file__)),indent=2)+'\n')
