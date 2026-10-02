#!/usr/bin/env python3
"""Compare replayed scientific outputs with historical expected outputs.

Timing/allocation values are intentionally not expected to match across hosts.
The near-checker logger's two encodings of empty geometry are equivalent here;
nonempty geometry, actions, and verdicts remain part of the comparison.
"""
import argparse, hashlib, json
from pathlib import Path
FILES={
 'controlled':['summary.json'],
 'controlled-trace':['summary.json'],
 'controlled-controls':['summary.json'],
 'controlled-audit':['observation_equivalence.json','velocity_audit.json','geometry_audit.json'],
 'checker-near':['results.json'], 'checker-far':['results.json'],
 'repairs':['summary.json'],
 'pruning-development':['development/results.json'],
 'pruning-validation':['validation/results.json'],
 'pruning-mature-only':['mature_only_ablation/D1_subset_fork__mature_only_off.json'],
 'native-search':['development_summary.json'],
 'native-attribution':['representative_attribution/summary.json'],
 'native-wrapper':['summary.json'],
}
COST_KEYS={'traced_wall_seconds','update_total_median_ms','update_total_min_ms','update_total_max_ms','update_total_p90_ms','timed_max_epoch_ms','offline_coverage_total_ms','python_update_peak_additional_bytes'}
def normalize(x):
 if isinstance(x,dict):
  if x.get('type') in ['GeometryCollection','Polygon'] and not x.get('coordinates') and not x.get('geometries'):return {'type':'EmptyGeometry'}
  return {k:normalize(v) for k,v in x.items() if k not in COST_KEYS}
 if isinstance(x,list):return [normalize(v) for v in x]
 if isinstance(x,float) and x.is_integer():return int(x)
 return x
def fingerprint(x):return hashlib.sha256(json.dumps(normalize(x),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('experiment',choices=sorted(FILES));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 expected=json.loads(Path(__file__).with_name('expected_results.json').read_text())[a.experiment]
 rows=[]
 for name in FILES[a.experiment]:
  path=a.output/name
  actual=fingerprint(json.loads(path.read_text()))
  rows.append(dict(file=name,expected_sha256=expected[name],actual_sha256=actual,passed=actual==expected[name]))
 report=dict(experiment=a.experiment,status='passed' if all(r['passed'] for r in rows) else 'failed',comparisons=rows,scope='Scientific-output comparison; not host-independent timing, full continuous soundness, or physical collision measurement.')
 print(json.dumps(report,indent=2))
 return 0 if report['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
