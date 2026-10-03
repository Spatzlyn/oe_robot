#!/usr/bin/env python3
"""Run an archived experiment with portable paths and a fresh output directory.

Native algorithms, observation schedules, candidate values and intervention
conditions are retained. The saved-results validator is artifact/validate_offline_v3.py.
This launcher actually executes native implementation code and never downloads data.
"""
import argparse, gzip, hashlib, json, os, runpy, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'reproduce'
COMMANDS={
 'controlled':('controlled/run_small_graph.py',[]),
 'controlled-controls':('controlled/verify_controls.py',[]),
 'controlled-audit':('controlled/audit_manuscript.py',[]),
 'ancillary-audit':('controlled/audit_manuscript.py',['--include-ancillary']),
 'controlled-trace':('controlled/trace_minimum.py',[]),
 'checker-near':('checker/check_actions.py',[]),
 'checker-far':('checker/check_actions.py',['--offset','100','--isolate-lane']),
 'repairs':('repairs/run_sufficiency.py',[]),
 'pruning-development':('pruning/run_boundaries.py',['--phase','development']),
 'pruning-validation':('pruning/run_boundaries.py',['--phase','validation']),
 'pruning-mature-only':('pruning/run_mature_only_ablation.py',[]),
 'native-search':('pruning/run_native_search.py',[]),
 'native-attribution':('pruning/audit_representative.py',[]),
 'native-wrapper':('pruning/run_wrapper_check.py',[]),
}
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def prepare_map():
 spec=json.loads((ROOT/'fixtures/map/map_manifest.json').read_text())
 src=ROOT/'fixtures/map'/spec['filename']
 assert digest(src)==spec['compressed_sha256'],'Map archive hash mismatch'
 cache=ROOT/'.cache/native_fixtures';cache.mkdir(parents=True,exist_ok=True)
 target=cache/spec['uncompressed_filename']
 if not target.exists():
  temp=target.with_suffix('.tmp')
  with gzip.open(str(src),'rb') as inp,temp.open('wb') as out:shutil.copyfileobj(inp,out)
  assert digest(temp)==spec['uncompressed_sha256'],'Map decompression hash mismatch'
  temp.replace(target)
 assert digest(target)==spec['uncompressed_sha256'],'Map payload hash mismatch'
 return target

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('experiment',choices=sorted(COMMANDS))
 p.add_argument('--output',required=True,type=Path,help='New directory; existing outputs are never overwritten')
 p.add_argument('--small-run',type=Path,help='Use a newly reproduced controlled directory for checker input')
 a=p.parse_args();out=a.output.resolve()
 if out.exists():p.error('Output already exists; choose a new directory.')
 out.parent.mkdir(parents=True,exist_ok=True)
 upstream=ROOT/'vendor/rss_occlusion'
 if not (upstream/'risk_analysis/shadow_utils.py').exists():p.error('Missing pinned vendor/rss_occlusion; see environment/README.md')
 sys.path[:0]=[str(HERE/'_common'),str(upstream),str(HERE/'pruning')]
 os.environ['OE_OUTPUT']=str(out)
 os.environ.setdefault('MPLBACKEND','Agg')
 os.environ.setdefault('PYGLET_HEADLESS','true')
 script,extra=COMMANDS[a.experiment];argv=[str(HERE/script)]+extra
 if a.experiment.startswith(('controlled','checker')) or a.experiment=='ancillary-audit':
  argv+=['--output',str(out)]
  if a.experiment in ('controlled-audit','ancillary-audit'):
   for key,path in [('small-run','fixtures/controlled'),('control-run','fixtures/audit/controls'),('action-run','fixtures/audit/near'),('far-run','fixtures/audit/far'),('trace-run','fixtures/audit/trace')]:
    argv+=['--'+key,str(ROOT/path)]
  if a.experiment.startswith('checker'):
   argv+=['--map',str(prepare_map())]
   if a.small_run:argv+=['--small-run',str(a.small_run.resolve())]
 else:
  out.mkdir()
  if a.experiment=='repairs':
   shutil.copyfile(str(HERE/'repairs/protocol.json'),str(out/'protocol.json'))
  elif a.experiment.startswith('pruning'):
   shutil.copyfile(str(HERE/'pruning/constructed_protocol.json'),str(out/'protocol.json'))
  elif a.experiment=='native-search':
   shutil.copyfile(str(HERE/'pruning/development_protocol.json'),str(out/'development_protocol.json'))
  elif a.experiment=='native-attribution':
   shutil.copyfile(str(HERE/'pruning/representative_attribution_protocol.json'),str(out/'representative_attribution_protocol.json'))
  elif a.experiment=='native-wrapper':
   shutil.copyfile(str(HERE/'pruning/wrapper_protocol.json'),str(out/'protocol.json'))
 sys.argv=argv
 runpy.run_path(str(HERE/script),run_name='__main__')

if __name__=='__main__':main()
