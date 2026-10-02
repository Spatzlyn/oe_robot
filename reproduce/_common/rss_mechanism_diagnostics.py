"""Offline original safety calls with measured intermediate values, no policy edits."""
import copy
import inspect
import sys
import numpy as np
from rss_trace import snapshot


def apply_context(planner, data):
    data=copy.deepcopy(data)
    space=planner.infoSpace
    for key,values in data['lane_state'].items():
        for attr,value in values.items():setattr(space.road_network.id_map[key],attr,value)
    space.shadow_manager.shadow_list=data['shadow_list']
    space.shadow_manager.risky_lane=data['risky_lane']
    # Stationary recorded objects are reconstituted without live actor access.
    from risk_analysis.object_utils import VehicleRecord,Bbox
    space.object_manager.obstacle_list={}
    for values in data['obstacles']:
        rec=VehicleRecord.__new__(VehicleRecord)
        for key,value in values.items():
            if key not in ['bbox','waypoint']:setattr(rec,key,value)
        road,section,lane,s=values['waypoint']
        rec.waypoint=space.client.map.get_waypoint_xodr(road,lane,s)
        rec.actor=None
        rec.bbox=Bbox.__new__(Bbox);rec.bbox.__dict__.update(values['bbox'])
        space.object_manager.obstacle_list[rec.id]=rec
    for key,value in data['checker'].items():setattr(space.state_checker,key,value)
    space.reset_prediction()
    return data


class Margins:
    """Record native stop slack and FRS/danger intersections, not a new certificate."""
    def __init__(self):self.records=[];self.current=None
    def __enter__(self):
        from shapely.geometry.base import BaseGeometry
        from risk_analysis.shadow_utils import ShadowUtils
        self.BaseGeometry=BaseGeometry
        self.ShadowUtils=ShadowUtils
        self.old_disjoint=BaseGeometry.disjoint
        self.old_bound=ShadowUtils.calc_V_max
        self.old_trace=sys.gettrace()
        def disjoint(a,b):
            value=self.old_disjoint(a,b)
            frame=inspect.currentframe().f_back
            if self.current is not None and frame.f_code.co_name in ['_check_intersection_bwd','_plan_close_loop_ego']:
                loc=frame.f_locals
                intersection=a.intersection(b)
                frs,zone=(b,a) if frame.f_code.co_name=='_plan_close_loop_ego' else (a,b)
                self.records.append(dict(action=self.current,function=frame.f_code.co_name,
                    source_line=frame.f_lineno,lane=loc.get('cur_lanelet_id',loc.get('lanelet_id_check')),
                    disjoint=bool(value),FRS=frs.__geo_interface__,danger_zone=zone.__geo_interface__,
                    overlap_area_m2_per_s=float(intersection.area),
                    raw_coordinate_distance=float(a.distance(b)),
                    distance_warning='Euclidean distance mixes position and speed; not a physical safety margin',
                    intersection_geometry=(intersection.__geo_interface__ if not intersection.is_empty
                        else dict(type='GeometryCollection',geometries=[])),
                    shadow=snapshot(loc['shadow']) if frame.f_code.co_name=='_check_intersection_bwd' and frame.f_lineno>=830 and 'shadow' in loc else None))
            return value
        def bound(manager,*args,**kwargs):
            value=self.old_bound(manager,*args,**kwargs)
            if self.current is not None:self.records.append(dict(action=self.current,function='calc_V_max',
                inbound=snapshot(args[0]),distance_m=float(args[1]),time_s=float(args[2]),value_m_per_s=float(value)))
            return value
        def trace(frame,event,arg):
            name=frame.f_code.co_name
            if name not in ['_is_safe_intersection','_check_intersection_bwd','_plan_close_loop_ego']:
                return None
            if event=='return' and self.current is not None:
                loc=frame.f_locals
                row=dict(action=self.current,function=name,event='return',result=snapshot(arg))
                for key in ['p_enter_rel','stop_dis','first_risk_dis','first_risk_v','slow_ok','fast_ok','first_intersection','first_shadow','a_plan','a_brake_shadow','a_brake_obj','a_brake_lane_end','v_shield']:
                    if key in loc:row[key]=snapshot(loc[key])
                if 'p_enter_rel' in loc:row['stop_slack_m']=float(loc['p_enter_rel']-loc['stop_dis'])
                self.records.append(row)
            return trace
        BaseGeometry.disjoint=disjoint
        ShadowUtils.calc_V_max=bound
        sys.settrace(trace)
        return self
    def __exit__(self,*args):
        sys.settrace(self.old_trace)
        self.BaseGeometry.disjoint=self.old_disjoint
        self.ShadowUtils.calc_V_max=self.old_bound


def evaluate_actions(planner, shadow_map, actions):
    result=[]
    with Margins() as metrics:
        for action in actions:
            metrics.current=list(action)
            checked=planner.infoSpace.state_checker.is_safe_plan(*action,
                planner.infoSpace.object_manager.predict_obstacle,shadow_map,use_record=True,debug=False)
            result.append(dict(input=list(action),result=snapshot(checked)))
    return dict(checks=result,metrics=metrics.records)
