"""Independent small geometry plus original backward shadow implementation."""
from types import SimpleNamespace as NS
import numpy as np
import client  # Import order required by pinned repository.
import planning
from risk_analysis.shadow import Shadow, InOutBound
from risk_analysis.shadow_utils import ShadowUtils

class Lane:
    def __init__(self, identifier, length, predecessor=(), successor=()):
        self.lanelet_id=identifier;self.lane_id=1;self.length=length
        self.waypoint_ds=np.arange(length,-.01,-.5)
        self.predecessor=list(predecessor);self.successor=list(successor)
        self.adj_same=[];self.adj_oppo=[];self.merge=None;self.cross=None
        self.waypoint_map={}
    def update(self,ds,value):self.waypoint_map[ds]=value

class Network:
    def __init__(self,lanes):self.id_map={lane.lanelet_id:lane for lane in lanes}
    def find_lane_id(self,key):return self.id_map[key]

def manager(connected=True):
    m=ShadowUtils.__new__(ShadowUtils)
    m.road_network=Network([Lane(1,20,successor=[2] if connected else []),Lane(2,10,predecessor=[1])])
    m.route=NS(in_ego_path=lambda key:True)
    m.v_max=15.;m.a_max_accel=4.;m.a_max_decel=8.;m.ds=.5
    m.shadow_stop_length=40;m.risky_lane=[1,2];m.shadow_list=[]
    return m

def flat_shadow(lo=3.,hi=15.,t=2.,t_in=0.):
    s=Shadow();s.risk_bound=False;s.parent_id=999
    s.root=InOutBound(1,hi,lo,t_in,t);s.leaf_list=[s.root];s.leaf_depth=[hi-lo]
    return s

def field(lane,ds,data,pose,t):
    if lane.lanelet_id==2:return True
    if ds>=15:return True
    if t==2.5:return ds<=1.5 or 2.5<=ds<=3
    if t==3.:return ds<=1 or 2<=ds<=3
    if t==3.5:return ds<=3.5
    if t==4.:return ds<=4.
    return ds<=3
