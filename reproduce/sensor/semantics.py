"""Finite-tree position projection and independent ideal-body certificate.
Copied from the existing offline v3 verifier; no native imports.
"""
import itertools

def position(forest,lane,ds,lengths,ignore_forward=False):
    """Position overapproximation only. Unresolved if any applicable tail remains.

    Finite terminal InBound is bounded by lane endpoint in backward trees.
    Positive IDs decrease ds in traffic direction in this corpus.
    """
    intervals=[];unknown=[]
    def walk(n,index):
        lid=n['id'];typ=n['type'];children=n.get('children') or []
        if lid not in lengths:unknown.append([index,'unknown_lane',lid]);return
        if typ=='InOutBound':lo,hi=n.get('ds_out'),n.get('ds_in')
        elif typ=='InBound':lo,hi=0,n.get('ds_in')
        elif typ=='OutBound':lo,hi=n.get('ds_out'),lengths[lid]
        elif typ=='ShadowNode':lo,hi=0,lengths[lid]
        else:unknown.append([index,'unknown_type',typ]);return
        if lo is None or hi is None:unknown.append([index,'missing_bound'])
        elif lid==lane:intervals.append([min(lo,hi),max(lo,hi)])
        if not children and typ not in ['InBound','InOutBound']:
            unknown.append([index,'unbounded_terminal',typ])
        for c in children:walk(c,index)
    for i,s in enumerate(forest):
        if ignore_forward and s['risk_bound']:continue
        if any(d is None for d in s.get('leaf_depth',[])):unknown.append([i,'truncated_leaf_depth'])
        walk(s['root'],i)
    present=any(a<=ds<=b for a,b in intervals)
    return dict(status='present' if present else 'unresolved' if unknown else 'absent',
                position_present=present,absence_supported=not unknown,unknown=unknown,intervals=intervals)

def body_hidden(x,gap):
    points=[]
    for bx,by,bz in itertools.product([8.,11.],[-.5,.5],[0.,1.5]):
        a=5/(10+by);points.append([x+a*(bx-x),1.7+a*(bz-1.7)])
    bounds=[min(p[0] for p in points),max(p[0] for p in points),
            min(p[1] for p in points),max(p[1] for p in points)]
    margin=min(bounds[0]-gap,5.5-bounds[1],bounds[2],4-bounds[3])
    return dict(feasible=margin>0,bounds=bounds,strict_margin=margin,
                scope='stationary 3x1x1.5 m body occlusion under fixed ideal panel geometry; linear camera segments bounded by endpoints')

