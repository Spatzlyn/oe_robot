"""Independent exact finite-state reach/observe calculation using rational arithmetic.

No imports from RSS or any shadow/deduplication algorithm. State q is the front
of a 3 m object in the direction of travel; footprint is [q-3,q]. The finite
control alphabet is a valid subset of the continuous bounded-acceleration model.
Positive witnesses are continuous feasible trajectories; no-witness is not a
continuous soundness proof.
"""
from fractions import Fraction as F

def frac(x):return x if isinstance(x,F) else F(str(x))

def transition(state, acceleration, dt=F(1,2), vmax=F(15)):
    q,v=state;a=frac(acceleration);dt=frac(dt)
    if a==0:return (q+v*dt,v)
    terminal=v+a*dt
    if 0<=terminal<=vmax:return (q+v*dt+a*dt*dt/2,terminal)
    boundary=F(0) if terminal<0 else vmax
    hit=(boundary-v)/a
    return (q+v*hit+a*hit*hit/2+boundary*(dt-hit),boundary)

def hidden(state, visible_intervals, length=F(3), domain=(F(-20),F(10))):
    q,_=state;left=q-length
    if left<domain[0] or q>domain[1]:return False
    return not any(max(left,a)<=min(q,b) for a,b in visible_intervals)

def clearance(state, visible_intervals, length=F(3)):
    q,_=state
    return min((max(a-q,(q-length)-b,F(0)) for a,b in visible_intervals),default=None)

def field_intervals(samples, domain=(-20,10)):
    """Nearest-sample piecewise-constant field; adjacent visible cells union."""
    samples=sorted((frac(q),bool(visible)) for q,visible in samples)
    intervals=[]
    for i,(q,visible) in enumerate(samples):
        if not visible:continue
        left=frac(domain[0]) if i==0 else (samples[i-1][0]+q)/2
        right=frac(domain[1]) if i==len(samples)-1 else (q+samples[i+1][0])/2
        if intervals and left<=intervals[-1][1]:intervals[-1]=(intervals[-1][0],right)
        else:intervals.append((left,right))
    return intervals

def propagate(initial, times, fields, controls=(-8,-4,0,4)):
    layers=[{s:None for s in initial if hidden(s,fields[times[0]])}]
    for prev,t in zip(times,times[1:]):
        layer={}
        for state in sorted(layers[-1]):
            for a in controls:
                nxt=transition(state,a,frac(t)-frac(prev))
                if t in fields and not hidden(nxt,fields[t]):continue
                if nxt not in layer:layer[nxt]=(state,a)
        layers.append(layer)
    return layers

def witness(layers,times,state,step):
    path=[]
    for i in range(step,-1,-1):
        parent=layers[i][state]
        path.append(dict(t=times[i],q=float(state[0]),v=float(state[1]),
                         q_exact=str(state[0]),v_exact=str(state[1]),
                         previous_acceleration=None if parent is None else parent[1]))
        if parent is not None:state=parent[0]
    return list(reversed(path))
