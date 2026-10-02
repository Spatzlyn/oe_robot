"""Coverage diagnostics. Never use a patched shadow output as reference truth."""
import copy
import hashlib
import inspect
import json
import textwrap
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def compact(shadow):
    def node(n):
        fields = {k: getattr(n, k) for k in ['id', 'ds_in', 'ds_out', 't_in', 't_out'] if hasattr(n, k)}
        for key in ['ds_in_hist', 't_in_hist']:
            if hasattr(n, key):
                value = getattr(n, key)
                fields[key] = None if value is None else [np.asarray(x).tolist() for x in value]
        return dict(type=type(n).__name__, **fields, children=[node(c) for c in n.child_node or []])
    return dict(risk_bound=shadow.risk_bound, parent=shadow.parent_id,
                root=node(shadow.root), leaf_depth=list(shadow.leaf_depth))

def position_segments(shadows, network):
    """Superset positional envelope of explicit nodes; flag implicit tails.

    Ignoring speed/history only enlarges this envelope, so absence is decisive
    on a closed single lane. Network implicit tails need a separate check.
    """
    out = []
    for index, shadow in enumerate(shadows):
        def visit(node):
            lane = network.find_lane_id(node.id)
            start, end = (lane.length, 0.) if lane.lane_id > 0 else (0., lane.length)
            inbound = getattr(node, 'ds_in', start)
            outbound = getattr(node, 'ds_out', end)
            out.append(dict(shadow=index, lane=int(node.id), lo=float(min(inbound, outbound)),
                            hi=float(max(inbound, outbound)), node_type=type(node).__name__,
                            implicit_tail=node.child_node is None and not (hasattr(node, 'ds_in') and hasattr(node, 'ds_out')),
                            risk_bound=shadow.risk_bound))
            for child in node.child_node or []:
                visit(child)
        visit(shadow.root)
    return out

def covers_position(segments, lane, s):
    return [x for x in segments if x['lane'] == lane and x['lo'] <= s <= x['hi']]

def instrument_update(mode='original'):
    """Original body, tracing at reduction sites without changing inputs."""
    from risk_analysis.shadow_utils import ShadowUtils
    original = ShadowUtils._update_shadow
    source = textwrap.dedent(inspect.getsource(original))
    records = []
    def emit(stage, t, shadow, **extra):
        records.append(dict(stage=stage, t=t, shadow=compact(shadow), **extra))
    code = source.replace('bound_lane_id = cur_shadow.root.id',
        "bound_lane_id = cur_shadow.root.id\n        emit('pop', t, cur_shadow)")
    code = code.replace('if bound_lane_id in bwd_visited_lane:',
        "emit('visited_test', t, cur_shadow, rejected=bound_lane_id in bwd_visited_lane)\n            if bound_lane_id in bwd_visited_lane:")
    code = code.replace('if new_shadow_begin not in bwd_searched_begin:',
        "emit('admission_test', t, new_shadow, rejected=new_shadow_begin in bwd_searched_begin, keys=list(bwd_searched_begin))\n                    if new_shadow_begin not in bwd_searched_begin:")
    # The fwd branch is indented four spaces deeper than the bwd branch.
    code = code.replace("                        emit('admission_test'", "                        emit('admission_test'")
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if "emit('admission_test'" in line:
            indent = len(line) - len(line.lstrip())
            lines[i+1] = ' ' * indent + lines[i+1].lstrip()
    code = '\n'.join(lines) + '\n'
    code = code.replace('if not check_repeate(mature_shadow):',
        "if not trace_repeat(mature_shadow, t, check_repeate):")
    def repeat(shadow, t, fn):
        result = fn(shadow)
        emit('mature_test', t, shadow, rejected=result)
        return result
    scope = dict(original.__globals__, emit=emit, trace_repeat=repeat)
    exec(compile(code, 'traced_shadow_update.py', 'exec'), scope)
    return original, scope['_update_shadow'], records, code
