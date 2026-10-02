#!/usr/bin/env python3
"""Audit saved synthetic-sensor records without importing/running the native planner.

Requires NumPy. --pixel-check recomputes independent slab intersections for
the stored depth images; otherwise that measurement remains historical.
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
from semantics import position, body_hidden

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def pixel_audit(case):
    """AABB slab intersections independently of the renderer's plane intersections."""
    poses=read(case/'sensor_poses.json'); rows=[]
    with np.load(str(case/'depth.npz')) as arrays:
        for i in range(9):
            images=arrays['frame_%02d'%i];_,h,w=images.shape
            f=w/(2*np.tan(110*np.pi/360))
            u,v=np.meshgrid(np.arange(w),np.arange(h))
            local=np.stack([np.ones_like(u),(u-w/2)/f,-(v-h/2)/f],axis=-1)
            changed=0;hit_count=0
            for k in range(4):
                p=np.asarray(poses[i][k]);origin=p[:3,3];rays=local@p[:3,:3].T
                lo=np.full((h,w),-np.inf);hi=np.full((h,w),np.inf)
                for d,(a,b) in enumerate([(8,11),(-.5,.5),(0,1.5)]):
                    with np.errstate(divide='ignore',invalid='ignore'):
                        x=(a-origin[d])/rays[:,:,d];y=(b-origin[d])/rays[:,:,d]
                    lo=np.maximum(lo,np.minimum(x,y));hi=np.minimum(hi,np.maximum(x,y))
                hit=(hi>=np.maximum(lo,0))&(hi>0)
                candidate=np.where(hit,np.maximum(lo,0),1000).astype(np.float32)
                changed+=int(np.count_nonzero(np.minimum(images[k],candidate)!=images[k]))
                hit_count+=int(np.count_nonzero(hit))
            rows.append(dict(t=i/2,image_width=w,image_height=h,body_intersecting_pixels=hit_count,
                             changed_depth_pixels_with_body=changed))
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--pixel-check',action='store_true')
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    checks=[];epochs=[];counts={};valid=0
    def check(name,ok):checks.append(dict(name=name,passed=bool(ok)))
    manifest=read(HERE/'public_manifest.json')
    for r in manifest['files']:
        p=HERE/r['path']
        check('distributed_hash/'+r['path'],p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'])
    for group in ['development_v1','confirmation_v3','native_resolution_control','native_resolution_local']:
        summaries=read(HERE/'expected'/group/'summary.json');counts[group]=len(summaries)
        for summary in summaries:
            case=HERE/'expected'/group/summary['case'];method=summary['method']
            run=read(case/(method+'.json'));plain=read(case/(method+'_plain.json'));scene=read(case/'scene.json')
            prefix=group+'/'+summary['case']+'/'+method
            check(prefix+'/completed',run['status']=='completed' and run['error'] is None)
            valid+=int(run['status']=='completed')
            for key in ['steps','status','intervention_applied']:
                check(prefix+'/traced_plain/'+key,run[key]==plain[key])
            lengths={int(k):max(v['ds']) for k,v in scene['lanes'].items()}
            for step in run['steps']:
                cert=body_hidden(step['ego_x'],run['config']['gap'])
                status=position(step['final'],1,8,lengths)
                check(prefix+'/witness_certificate/'+str(step['t']),cert['feasible']==step['witness']['all_body_hidden'])
                if status['status']=='present':classification='position_present'
                elif status['status']=='unresolved':classification='semantic_unresolved'
                elif cert['feasible']:classification='feasible_position_absent'
                else:classification='witness_not_certified'
                epochs.append(dict(group=group,case=summary['case'],method=method,t=step['t'],
                    body_feasible=cert['feasible'],position_status=status['status'],classification=classification,
                    historical_status=step['witness_status'],outputs=len(step['final']),
                    permission='unmeasured',collision='unmeasured',task_completion='unmeasured'))
    for resolution,group,local_group,target in [(640,'confirmation_v3','confirmation_v3',2.),(1920,'native_resolution_control','native_resolution_local',3.5)]:
        original=read(HERE/'expected'/group/'v0.5_g-0.5/original.json')
        local=read(HERE/'expected'/local_group/'v0.5_g-0.5/single_admission.json')
        ix=int(target*2)
        check(str(resolution)+'/same_prefix',original['steps'][:ix]==local['steps'][:ix])
        check(str(resolution)+'/same_target_prior',original['steps'][ix]['prior']==local['steps'][ix]['prior'])
        target_spec=read(HERE/'protocols'/('sensor_%s.json'%resolution))['target']
        check(str(resolution)+'/one_target_grant',local['intervention_applied']==[target_spec])
        oi=[i for i,e in enumerate(original['events']) if e.get('stage')=='admission_observed' and e.get('t')==target and e.get('shadow')==target_spec['shadow']]
        li=[i for i,e in enumerate(local['events']) if e.get('stage')=='admission_observed' and e.get('t')==target and e.get('shadow')==target_spec['shadow']]
        check(str(resolution)+'/exact_event_prefix',len(oi)==len(li)==1 and original['events'][:oi[0]+1]==local['events'][:li[0]+1])
        expected={640:([2.,3.5,4.],[3.5,4.]),1920:([3.5],[])}[resolution]
        for run,times in zip([original,local],expected):
            absent=[s['t'] for s in run['steps'] if position(s['final'],1,8,{1:20,2:10,999:40})['status']=='absent']
            check(str(resolution)+'/'+run['method']+'/absent_times',absent==times)
    invalid=read(HERE/'expected/confirmation_v2/execution_failure.json')
    check('pre_native_instrumentation_failure_retained',invalid['native_episodes']==0 and invalid['status']=='invalid_instrumentation_before_native_execution')
    if args.pixel_check:
        observed={g:pixel_audit(HERE/'expected'/g/'v0.5_g-0.5') for g in ['confirmation_v3','native_resolution_control']}
        historical=read(HERE/'historical_analysis/body_sensor_noninterference.json')['results']
        for group,rows in observed.items():check('pixel_audit/'+group,rows==historical[group])
        dump(out/'recomputed_body_pixel_audit.json',observed)
    with (out/'epoch_matrix.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(epochs[0]));writer.writeheader();writer.writerows(epochs)
    result=dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks,
        failed=sum(not c['passed'] for c in checks),historical_traced_sequences=valid,historical_plain_sequences=valid,
        historical_epoch_records=len(epochs),historical_native_update_calls=len(epochs)*2,
        historical_instrumentation_failures_before_native=1,cohort=counts,new_native_runs=0,
        pixel_test_reexecuted=args.pixel_check,scope='Nine related development geometry/motion conditions; selected replay and resolution conditions overlap, not independent scenes. Position projection; no whole continuous soundness or action-safety certificate.')
    dump(out/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
    if result['failed']:raise SystemExit(1)

if __name__=='__main__':main()
