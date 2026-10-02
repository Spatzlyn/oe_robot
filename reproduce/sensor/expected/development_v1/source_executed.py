#!/usr/bin/env python3
"""Fixed-scene full-image depth rendering → unmodified native visibility/update.
Synthetic road/client boundary; no hand-constructed Shadow enters the manager.
"""
import argparse, copy, datetime, hashlib, inspect, json, math, os, sys, textwrap, traceback
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np

ROOT=Path('<PROJECT_ROOT>')
sys.path.insert(0,str(ROOT/'analysis/semantic_coverage'))
from small_graph import Lane, Network
from common import compact, position_segments
from conservative_reduction import make
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.visibility_checker import DepthVisibility

W,H=640,360
F=W/(2*np.tan(110*np.pi/360))
TIMES=[i/2 for i in range(9)]
ORIGINAL=ShadowUtils._update_shadow

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,default=lambda v:v.item() if isinstance(v,np.generic) else str(v))+'\n')

class Pose:
    def __init__(self,x,y,z,yaw):
        c,s=math.cos(yaw),math.sin(yaw)
        self.matrix=np.array([[c,-s,0,x],[s,c,0,y],[0,0,1,z],[0,0,0,1.]])
    def get_inverse_matrix(self):return np.linalg.inv(self.matrix).tolist()

def render(x,gap):
    """Each pixel ray intersects the SAME fixed vertical panels and ground plane."""
    u,v=np.meshgrid(np.arange(W),np.arange(H))
    local=np.stack([np.ones_like(u),(u-W/2)/F,-(v-H/2)/F],axis=-1)
    origin=np.array([x,-10.,1.7]); images=[];poses=[]
    panels=[[-1.,-.75],[gap,5.5]]
    for k in range(4):
        pose=Pose(x,-10,1.7,k*np.pi/2);poses.append(pose)
        rays=local@pose.matrix[:3,:3].T
        depth=np.full((H,W),1000.,dtype=np.float64)
        with np.errstate(divide='ignore',invalid='ignore'):
            hit=(-5-origin[1])/rays[:,:,1]
            px=origin[0]+hit*rays[:,:,0];pz=origin[2]+hit*rays[:,:,2]
            for lo,hi in panels:
                mask=(hit>0)&(px>=lo)&(px<=hi)&(pz>=0)&(pz<=4)
                depth[mask]=np.minimum(depth[mask],hit[mask])
            ground=-origin[2]/rays[:,:,2]
            mask=ground>0
            depth[mask]=np.minimum(depth[mask],ground[mask])
        images.append(depth.astype(np.float32))
    return images,poses

def geometry(lane):
    d=lane.waypoint_ds
    if lane.lanelet_id==1: x,y=d,np.zeros_like(d)
    elif lane.lanelet_id==2:x,y=d-10,np.zeros_like(d)
    else:x,y=np.where(d>=20,20-d,0),np.where(d>=20,-10,10-d)
    lane.center_vertices=np.stack([x,y,np.zeros_like(d),np.ones_like(d)],axis=1)
    lane.left_vertices=lane.center_vertices.copy();lane.left_vertices[:,1]+=.5
    lane.right_vertices=lane.center_vertices.copy();lane.right_vertices[:,1]-=.5
    lane.lane_section=NS(s_start=0.)

def manager():
    m=ShadowUtils.__new__(ShadowUtils)
    a,b,e=Lane(1,20,successor=[2]),Lane(2,10,predecessor=[1]),Lane(999,40)
    e.cross=[1,2]
    for l in [a,b,e]:geometry(l)
    n=Network([a,b,e]); n.find_lane=lambda road,section,lane:n.id_map[999]
    m.road_network=n;m.route=NS(in_ego_path=lambda key:key==999)
    m.v_max=15.;m.a_max_accel=4.;m.a_max_decel=8.;m.ds=.5
    m.shadow_stop_length=40;m.risky_lane=[];m.shadow_list=[]
    m.vis_checker_depth=DepthVisibility(n,100,img_width=W,img_height=H,h_fov=110)
    m.client=NS(ego=NS(get_location=lambda:NS(x=m.ego_x,y=-10,z=0)),
        map=NS(get_waypoint=lambda loc,**kwargs:NS(road_id=999,section_id=0,lane_id=1,s=20-loc.x)))
    return m

def witness_certificate(x,gap):
    # For every point in body x∈[8,11],y∈[-.5,.5],z∈[0,1.5], segment to
    # sensor crosses y=-5 at alpha=5/(10+y). The endpoint extrema are bounds
    # of the fractional affine coordinate on this rectangle.
    points=[]
    for bx in [8,11]:
        for by in [-.5,.5]:
            for bz in [0,1.5]:
                alpha=5/(10+by)
                points.append([x+alpha*(bx-x),1.7+alpha*(bz-1.7)])
    a=np.array(points); xr=[float(a[:,0].min()),float(a[:,0].max())];zr=[float(a[:,1].min()),float(a[:,1].max())]
    return dict(body_ds=[8,11],body_y=[-.5,.5],body_z=[0,1.5],stationary_v=0,stationary_a=0,
        panel_intersection_x=xr,panel_intersection_z=zr,
        all_body_hidden=bool(gap<xr[0] and xr[1]<5.5 and 0<zr[0] and zr[1]<4),
        horizontal_margin=min(xr[0]-gap,5.5-xr[1]),
        proof='Fractional-affine ray/screen intersection extrema occur at rectangle endpoints; strict bounds inside right opaque panel. Same bounds over linear camera segment follow from affine dependence on camera x.')

def compile_method(method,target=None):
    source=textwrap.dedent(inspect.getsource(ORIGINAL));scope=dict(ORIGINAL.__globals__);applied=[]
    if method=='admission_off':source=source.replace('if new_shadow_begin not in bwd_searched_begin:','if True:')
    elif method=='mature_only_off':source=source.replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)','return False')
    elif method=='mature_guard':
        fn,source=make(ORIGINAL);scope=dict(fn.__globals__)
    elif method=='single_admission':
        def grant(s,t):
            yes=(not applied and t==target['t'] and compact(s)==target['shadow'])
            if yes:applied.append(dict(t=t,shadow=compact(s)))
            return yes
        scope['grant']=grant
        source=source.replace('if new_shadow_begin not in bwd_searched_begin:','if new_shadow_begin not in bwd_searched_begin or grant(new_shadow,t):')
    exec(compile(source,'method.py','exec'),scope)
    return scope['_update_shadow'],source,applied

def trace_method(fn,source,events):
    def emit(stage,t,s,**extra):events.append(dict(stage=stage,t=t,shadow=compact(s),**extra))
    code=source.replace('bound_lane_id = cur_shadow.root.id',"bound_lane_id = cur_shadow.root.id\n        emit('pop',t,cur_shadow)")
    code=code.replace('bwd_searched_begin.append((bound_lane_id, cur_shadow.root.ds_out))',"bwd_searched_begin.append((bound_lane_id, cur_shadow.root.ds_out))\n                emit('key_registered',t,cur_shadow,key=[bound_lane_id,cur_shadow.root.ds_out])")
    # Preserve the method's original condition; the extra line is passive.
    lines=code.splitlines();out=[]
    for line in lines:
        if line.lstrip().startswith('if ') and ('new_shadow_begin not in bwd_searched_begin' in line or 'any(dominates(prior, new_shadow)' in line):
            indent=line[:len(line)-len(line.lstrip())]
            out.append(indent+"emit('admission_observed',t,new_shadow,native_would_reject=new_shadow_begin in bwd_searched_begin,keys=list(bwd_searched_begin))")
        out.append(line)
    code='\n'.join(out)+'\n'
    code=code.replace('if not check_repeate(mature_shadow):','if not repeat(mature_shadow,t,check_repeate):')
    def repeat(s,t,f):
        r=f(s);emit('mature_test',t,s,rejected=bool(r));return r
    scope=dict(fn.__globals__,emit=emit,repeat=repeat)
    exec(compile(code,'traced_method.py','exec'),scope)
    return scope['_update_shadow'],code

def run(config,frames,method='original',traced=True,target=None):
    m=manager();events=[];steps=[];fn,source,applied=compile_method(method,target)
    if traced:fn,trace_source=trace_method(fn,source,events)
    else:trace_source=None
    m._update_shadow=fn.__get__(m,ShadowUtils)
    if traced:
        primitive=m._update_bwd_shadow
        def p(s,*args):
            before=compact(s);r=primitive(s,*args)
            events.append(dict(stage='primitive_return',t=args[-1],input=before,mature=None if r[0] is None else compact(r[0]),children=[compact(c) for c in r[1]],visited=r[2]))
            return r
        m._update_bwd_shadow=p
        create=m.create_shadow
        def c(*a,**kw):
            s=create(*a,**kw);events.append(dict(stage='native_create_shadow',args=list(a),shadow=compact(s)));return s
        m.create_shadow=c
    query=m.vis_checker_depth.check_visibility
    queries=[]
    def q(l,ds,imgs,poses,t):
        r=query(l,ds,imgs,poses,t)
        if traced:queries.append(dict(t=t,lane=l.lanelet_id,ds=float(ds),visible=bool(r)))
        return r
    m.vis_checker_depth.check_visibility=q
    try:
        for t,(images,poses) in zip(TIMES,frames):
            m.ego_x=-4+config['velocity']*t
            before=[compact(s) for s in m.shadow_list];initialized=not m.shadow_list
            maps,shadows=m.update_visibility(images,poses,t)
            seg=position_segments(shadows,m.road_network)
            present=any(s['lane']==1 and s['lo']<=8<=s['hi'] for s in seg)
            implicit=any(d is None for s in shadows for d in s.leaf_depth)
            # Any absent witness with a truncated tree is conservatively unresolved.
            cert=witness_certificate(m.ego_x,config['gap'])
            status='witness_position_present' if present else ('semantic_unresolved' if implicit else 'witnessed_omission' if cert['all_body_hidden'] else 'witness_not_certified')
            steps.append(dict(t=t,ego_x=m.ego_x,wrapper_reinitialization=initialized,prior=before,final=[compact(s) for s in shadows],segments=seg,risky_lane=list(m.risky_lane),witness=cert,witness_status=status))
        status='completed';error=None
    except Exception:
        status='invalid_execution';error=traceback.format_exc()
    return dict(config=config,method=method,traced=traced,status=status,error=error,steps=steps,events=events,visibility_queries=queries,intervention_applied=applied,method_source=source,trace_source=trace_source)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--confirm',type=Path);args=ap.parse_args()
    out=args.output;out.mkdir(exist_ok=False)
    dump(out/'start_manifest.json',dict(utc=datetime.datetime.utcnow().isoformat()+'Z',command=sys.argv,device='CPU',pid=os.getpid(),harness_sha256=sha(__file__),protocol_sha256=sha(Path(__file__).with_name('protocol_v1.md')),native={f:sha(ROOT/'repos/rss_occlusion/risk_analysis'/f) for f in ['shadow_utils.py','visibility_checker.py','shadow.py']}))
    configs=[dict(id='v{}_g{}'.format(v,g),velocity=v,gap=g) for v in [0,.5,1] for g in [-.5,-.25,0]]
    target=None;methods=['original']
    if args.confirm:
        frozen=json.loads(args.confirm.read_text());configs=[frozen['config']];target=frozen['target'];methods=frozen['methods']
    summaries=[]
    for cfg in configs:
        frames=[render(-4+cfg['velocity']*t,cfg['gap']) for t in TIMES]
        case=out/cfg['id'];case.mkdir()
        np.savez_compressed(str(case/'depth.npz'),**{'frame_%02d'%i:np.stack(fr[0]) for i,fr in enumerate(frames)})
        dump(case/'sensor_poses.json',[[p.matrix.tolist() for p in fr[1]] for fr in frames])
        mm=manager();dump(case/'scene.json',dict(config=cfg,panels=[dict(y=-5,x=[-1,-.75],z=[0,4]),dict(y=-5,x=[cfg['gap'],5.5],z=[0,4])],lanes={str(k):dict(center=l.center_vertices.tolist(),ds=l.waypoint_ds.tolist(),predecessor=l.predecessor,successor=l.successor,cross=l.cross) for k,l in mm.road_network.id_map.items()},camera=dict(width=W,height=H,h_fov=110,depth='camera forward-axis distance',far=1000,range=100)))
        for method in methods:
            r=run(cfg,frames,method,True,target);plain=run(cfg,frames,method,False,target)
            parity=r['steps']==plain['steps'] and r['status']==plain['status'] and r['intervention_applied']==plain['intervention_applied']
            r['instrumentation_parity']=parity
            dump(case/(method+'.json'),r);dump(case/(method+'_plain.json'),plain)
            row=dict(case=cfg['id'],method=method,status=r['status'],parity=parity,omission_times=[s['t'] for s in r['steps'] if s['witness_status']=='witnessed_omission'],unresolved_times=[s['t'] for s in r['steps'] if s['witness_status']=='semantic_unresolved'],applied=len(r['intervention_applied']),native_rejects=sum(e.get('native_would_reject',False) for e in r['events']),error=r['error'])
            summaries.append(row);print(json.dumps(row),flush=True)
    dump(out/'summary.json',summaries)
    (out/'source_executed.py').write_bytes(Path(__file__).read_bytes())
    dump(out/'completion.json',dict(utc=datetime.datetime.utcnow().isoformat()+'Z',traced_runs=len(summaries),plain_runs=len(summaries),valid=sum(x['status']=='completed' for x in summaries),invalid=sum(x['status']!='completed' for x in summaries)))

if __name__=='__main__':main()
