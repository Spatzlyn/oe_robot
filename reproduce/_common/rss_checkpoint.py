"""Restore the fixed checker input using CARLA's offline OpenDRIVE API."""
import pickle
from pathlib import Path
from types import SimpleNamespace as NS


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
