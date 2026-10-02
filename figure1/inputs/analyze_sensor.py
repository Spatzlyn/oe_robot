#!/usr/bin/env python3
"""Offline audit of saved artifacts; no native simulation or new intervention."""
import csv, hashlib, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

B=Path(__file__).resolve().parent
O=B/'analysis';O.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit_body(case):
    arrays=np.load(str(case/'depth.npz'));poses=read(case/'sensor_poses.json');rows=[]
    for i in range(9):
        images=arrays['frame_%02d'%i];_,h,w=images.shape;f=w/(2*np.tan(110*np.pi/360))
        u,v=np.meshgrid(np.arange(w),np.arange(h));local=np.stack([np.ones_like(u),(u-w/2)/f,-(v-h/2)/f],axis=-1)
        total=0;hit_count=0
        for k in range(4):
            p=np.asarray(poses[i][k]);origin=p[:3,3];rays=local@p[:3,:3].T
            # Independent slab intersection with a 3D witness volume; unlike
            # renderer's plane intersection, this evaluates an added object.
            lo=np.full((h,w),-np.inf);hi=np.full((h,w),np.inf)
            for d,(a,b) in enumerate([(8,11),(-.5,.5),(0,1.5)]):
                with np.errstate(divide='ignore',invalid='ignore'):
                    x=(a-origin[d])/rays[:,:,d];y=(b-origin[d])/rays[:,:,d]
                lo=np.maximum(lo,np.minimum(x,y));hi=np.minimum(hi,np.maximum(x,y))
            hit=(hi>=np.maximum(lo,0))&(hi>0)
            candidate=np.where(hit,np.maximum(lo,0),1000).astype(np.float32)
            total+=int(np.count_nonzero(np.minimum(images[k],candidate)!=images[k]))
            hit_count+=int(np.count_nonzero(hit))
        rows.append(dict(t=i/2,image_width=w,image_height=h,body_intersecting_pixels=hit_count,changed_depth_pixels_with_body=total))
    return rows

def main():
    datasets=['development_v1','confirmation_v3','native_resolution_control','native_resolution_local']
    runs=[];table=[]
    for group in datasets:
        if not (B/group/'summary.json').exists():continue
        for row in read(B/group/'summary.json'):
            p=B/group/row['case']/(row['method']+'.json');r=read(p);runs.append((group,p,r))
            cert=[s['witness']['all_body_hidden'] for s in r['steps']]
            row=dict(row,group=group,full_horizon_body_certified=all(cert),body_uncertified_times=';'.join(str(s['t']) for s in r['steps'] if not s['witness']['all_body_hidden']),raw=str(p.relative_to(B)))
            for k in ['omission_times','unresolved_times']:row[k]=';'.join(map(str,row[k]))
            table.append(row)
    with (O/'run_matrix.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    epochs=[]
    for group,p,r in runs:
        for s in r['steps']:
            epochs.append(dict(group=group,case=r['config']['id'],method=r['method'],t=s['t'],body_feasible=s['witness']['all_body_hidden'],body_margin_m=s['witness']['horizontal_margin'],witness_position=s['witness_status'],wrapper_reinitialization=s['wrapper_reinitialization'],output_count=len(s['final']),generic_segment_implicit_flag=any(x.get('implicit_tail') for x in s['segments']),truncated_leaf_depth=any(d is None for sh in s['final'] for d in sh['leaf_depth']),permission='unmeasured',collision='unmeasured',completion='unmeasured'))
    with (O/'epoch_matrix.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(epochs[0]));w.writeheader();w.writerows(epochs)
    case='v0.5_g-0.5';dev=B/'development_v1'/case;conf=B/'confirmation_v3'/case
    original=read(conf/'original.json');single=read(conf/'single_admission.json')
    parity=dict(development_v1_vs_logger_v3_steps=read(dev/'original.json')['steps']==original['steps'],
        development_vs_confirmation_depth=all(np.array_equal(np.load(str(dev/'depth.npz'))[k],np.load(str(conf/'depth.npz'))[k]) for k in np.load(str(dev/'depth.npz')).files),
        development_vs_confirmation_poses=read(dev/'sensor_poses.json')==read(conf/'sensor_poses.json'),
        local_same_prefix_before_t2=original['steps'][:4]==single['steps'][:4],
        local_same_target_epoch_prior=original['steps'][4]['prior']==single['steps'][4]['prior'],
        all_traced_plain_outputs=all(r['instrumentation_parity'] for _,_,r in runs))
    if (B/'native_resolution_local'/case/'single_admission.json').exists():
        no=read(B/'native_resolution_control'/case/'original.json');ns=read(B/'native_resolution_local'/case/'single_admission.json')
        parity['native_resolution_same_prefix_before_t3_5']=no['steps'][:7]==ns['steps'][:7]
        parity['native_resolution_same_prior_at_t3_5']=no['steps'][7]['prior']==ns['steps'][7]['prior']
        parity['native_resolution_same_sensor_arrays']=all(np.array_equal(np.load(str(B/'native_resolution_control'/case/'depth.npz'))[k],np.load(str(B/'native_resolution_local'/case/'depth.npz'))[k]) for k in np.load(str(B/'native_resolution_control'/case/'depth.npz')).files)
    dump(O/'parity.json',parity)
    body={g:audit_body(B/g/case) for g in ['confirmation_v3','native_resolution_control']}
    dump(O/'body_sensor_noninterference.json',dict(scope='Added stationary 3x1x1.5m body under saved depth/pose data. Pixel test complements analytic continuous body proof; no old two-observation equivalence reused.',results=body))
    # Minimal chain: include every event at the target epoch, retaining context.
    chain=[dict(index=i,**e) for i,e in enumerate(original['events']) if e.get('t')==2.]
    dump(O/'target_epoch_all_events.json',chain)
    selected=[]
    for i,e in enumerate(original['events']):
        if e.get('t')==2 and ((e['stage']=='key_registered' and e.get('key')==[1,1.5]) or
           (e['stage']=='primitive_return' and e['input']['root'].get('ds_out')==1.5 and e['input']['root'].get('ds_in')==2) or
           (e['stage']=='admission_observed' and e['shadow']['root'].get('ds_out')==1.5 and e['shadow']['root'].get('ds_in')==14.5)):
            selected.append(dict(index=i,**e))
    dump(O/'causal_chain.json',dict(events=selected,original_output=original['steps'][4]['final'],intervention_application=single['intervention_applied'],intervened_output=single['steps'][4]['final'],scope='same raw sensor sequence and identical native prefix to target admission; later recurrence retained'))
    fig,ax=plt.subplots(1,2,figsize=(13,5.2),gridspec_kw={'width_ratios':[1,1.3]})
    a=ax[0];a.plot([20,-10],[0,0],color='0.5',lw=5,label='Target road')
    a.plot([-20,0,0],[-10,-10,10],'--',color='0.5',label='Synthetic ego route')
    for lo,hi in [(-1,-.75),(-.5,5.5)]:a.plot([lo,hi],[-5,-5],color='black',lw=5)
    a.add_patch(Rectangle((8,-.5),3,1,color='#d95f02',label='Hidden witness body'))
    a.plot([-4,-2],[-10,-10],color='#1b9e77',lw=5,label='Observed camera motion')
    for x in [-4,-2]:
        for bx in [8,11]:a.plot([x,bx],[-10,0],color='#1b9e77',alpha=.4)
    a.set(xlim=(-5,16),ylim=(-12,4),xlabel='World x (m)',ylabel='World y (m)',title='Fixed panels; generated full depth images');a.set_aspect('equal');a.legend(fontsize=8,loc='upper right')
    labels=[];curves=[]
    for method in ['original','single_admission','admission_off','mature_only_off','mature_guard']:
        labels.append('640: '+method);curves.append(read(conf/(method+'.json')))
    for group,method in [('native_resolution_control','original'),('native_resolution_local','single_admission'),('native_resolution_control','admission_off')]:
        p=B/group/case/(method+'.json')
        if p.exists():labels.append('1920: '+method);curves.append(read(p))
    a=ax[1]
    for j,r in enumerate(curves):
        for s in r['steps']:
            ok=s['witness_status']=='witness_position_present'
            a.scatter(s['t'],j,c='#1b9e77' if ok else '#d95f02',marker='o' if ok else 'x',s=60)
    a.set_yticks(range(len(labels)));a.set_yticklabels(labels,fontsize=8);a.invert_yaxis();a.set_xticks([i/2 for i in range(9)]);a.set(xlabel='Native update time (s)',title='Witness position: circle present / cross absent');a.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(str(O/'sensor_evidence.pdf'));fig.savefig(str(O/'sensor_evidence.png'),dpi=170);plt.close(fig)
    dump(O/'summary.json',dict(completed_method_sequences=len(runs),native_sequences_including_plain=2*len(runs),native_update_calls=18*len(runs),invalid_pre_native_instrumentation_attempts=1,body_depth_change_pixels=sum(x['changed_depth_pixels_with_body'] for rows in body.values() for x in rows),all_parity_checks_pass=all(parity.values()),unresolved_epoch_count=sum(x['witness_position']=='semantic_unresolved' for x in epochs),all_9_scene_full_horizon_claim=False,independent_scenes='nine related development parameter conditions, not independent natural scenes',sha256=sh(__file__)))
    print(json.dumps(read(O/'summary.json'),indent=2))

if __name__=='__main__':main()
