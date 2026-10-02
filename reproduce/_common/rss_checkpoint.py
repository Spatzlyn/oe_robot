"""Serializable planning inputs; this is NOT a full CARLA restore snapshot.

Rebuilds the local road geometry with CARLA's offline OpenDRIVE API. Validation
must compare the entire replayed search with the recorded source search before
using a checkpoint for continuation diagnosis.
"""
import hashlib
import pickle
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np


def capture(planner, args, run_dir, cycle, method):
    space = planner.infoSpace
    if not hasattr(space, "road_network"):
        return None  # Synthetic instrumentation validation has no simulator state.
    folder = Path(run_dir) / "planning_inputs"
    folder.mkdir(exist_ok=True)
    xodr = folder / "Town01.xodr"
    if not xodr.exists():
        xodr.write_text(space.client.map.to_opendrive())
    obstacles = []
    for record in space.object_manager.obstacle_list.values():
        wp = record.waypoint
        scalar = {k: getattr(record, k) for k in ["id", "last_seen", "velocity", "a_max_decel", "a_max_accel", "v_min", "v_max"]}
        scalar.update(waypoint=[wp.road_id, wp.section_id, wp.lane_id, wp.s], bbox=record.bbox.__dict__.copy())
        obstacles.append(scalar)
    lane_state = {key: dict(waypoint_map=lane.waypoint_map, cross_ds=lane.cross_ds, merge_ds=lane.merge_ds)
                  for key, lane in space.road_network.id_map.items()}
    data = dict(format_version=1, scope="planning_inputs_not_full_simulator_state", method=method, cycle=cycle,
                state=list(args[:5]), shadow_map=args[5], shadow_list=space.shadow_manager.shadow_list,
                route=space.route.route, obstacles=obstacles, lane_state=lane_state,
                ego_id=space.client.ego_id, risky_lane=space.shadow_manager.risky_lane,
                shadow_stop_length=space.shadow_manager.shadow_stop_length,
                planning=dict(v_max=planner.v_max, a_max_accel=planner.a_max_accel,
                              a_max_decel=planner.a_max_decel, dt=planner.dt, T_plan=planner.T_plan),
                lattice=dict(dp=planner.lattice.dp, dl=planner.lattice.dl, dv=planner.lattice.dv,
                             dt=planner.lattice.dt, V_range=planner.lattice.V_range, t_range=planner.lattice.t_range),
                checker={k: getattr(space.state_checker, k) for k in ["v_max", "a_max_decel", "a_max_accel", "ego_width", "ego_length", "slack_distance", "search_stop", "v_min"]},
                sensor_range=space.shadow_manager.vis_checker_octomap.range, ds=space.shadow_manager.ds)
    raw = pickle.dumps(data, protocol=4)
    file = folder / ("cycle_%04d.pkl" % cycle)
    file.write_bytes(raw)
    return dict(ref=str(file.relative_to(run_dir)), sha256=hashlib.sha256(raw).hexdigest(),
                scope=data["scope"], validated=False)


def restore(file, octomap_file):
    # Only load checkpoints created by this harness from trusted local runs.
    import carla
    import client
    from mapping import RoadNetwork
    from planning import Route
    from planning.lattice.lattice import Lattice
    from planning.search.A_star import A_star
    from risk_analysis.info_space import ISpace
    from risk_analysis.shadow_utils import ShadowUtils
    from risk_analysis.object_utils import ObjectUtils, VehicleRecord, Bbox
    from risk_analysis.state_checker import StateChecker
    file = Path(file)
    data = pickle.loads(file.read_bytes())
    assert data["format_version"] == 1
    local_map = carla.Map("Town01", (file.parent / "Town01.xodr").read_text())
    context = NS(map=local_map, ego_id=data["ego_id"], world=NS(debug=None))
    space = ISpace.__new__(ISpace)
    space.client = context
    space.road_network = RoadNetwork(context)
    space.route = Route(context, space.road_network, data["route"])
    space.shadow_manager = ShadowUtils(context, space.road_network, str(octomap_file), space.route,
                                       data["sensor_range"], data["ds"], data["planning"]["v_max"], data["planning"]["a_max_decel"])
    space.object_manager = ObjectUtils(context, space.road_network)
    space.state_checker = StateChecker(context, space.road_network, space.route, space.shadow_manager,
                                       data["planning"]["v_max"], data["planning"]["a_max_decel"])
    for key, values in data["lane_state"].items():
        lane = space.road_network.id_map[key]
        for attr, value in values.items():
            setattr(lane, attr, value)
    for values in data["obstacles"]:
        record = VehicleRecord.__new__(VehicleRecord)
        for key, value in values.items():
            if key not in ["bbox", "waypoint"]:
                setattr(record, key, value)
        road, section, lane, s = values["waypoint"]
        record.waypoint = local_map.get_waypoint_xodr(road, lane, s)
        assert record.waypoint is not None
        record.actor = None  # Planning uses recorded velocity/waypoint, never actor.update.
        record.bbox = Bbox.__new__(Bbox)
        record.bbox.__dict__.update(values["bbox"])
        space.object_manager.obstacle_list[record.id] = record
    space.shadow_manager.shadow_list = data["shadow_list"]
    space.shadow_manager.risky_lane = data["risky_lane"]
    space.shadow_manager.shadow_stop_length = data["shadow_stop_length"]
    for key, value in data["checker"].items():
        setattr(space.state_checker, key, value)
    lattice = Lattice(space.route, **data["lattice"])
    lattice.reset(data["state"][0])
    planner = A_star(space, lattice, **data["planning"])
    return planner, data
