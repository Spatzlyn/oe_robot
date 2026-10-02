"""Observation-only wrappers around the pinned RSS planner (Python 3.6).

No extra predict/safety calls, no queue reordering, no merge-rule changes.
Snapshots encode mutable history values immediately, including graph references.
Parent history at merge is NOT the rejected node's uncomputed prediction.
"""
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np


def snapshot(value):
    seen = {}

    def encode(x):
        if isinstance(x, np.generic):
            return encode(x.item())
        if x is None or isinstance(x, (str, bool, int)):
            return x
        if isinstance(x, float):
            return x if math.isfinite(x) else {"nonfinite": str(x)}
        if isinstance(x, np.ndarray):
            return {"ndarray": encode(x.tolist()), "dtype": str(x.dtype), "shape": list(x.shape)}
        if isinstance(x, (list, tuple)):
            return [encode(y) for y in x]
        if isinstance(x, dict):
            return {str(k): encode(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
        if id(x) in seen:
            return {"ref": seen[id(x)]}
        key = len(seen)
        seen[id(x)] = key
        fields = getattr(type(x), "__slots__", ())
        if not fields:
            raise TypeError("Unsupported history type: " + type(x).__name__)
        return {"id": key, "type": type(x).__name__, "fields": {k: encode(getattr(x, k)) for k in fields}}

    return encode(value)


class Trace:
    def __init__(self, run_dir, evidence_level="planner_trace"):
        self.run_dir = Path(run_dir)
        self.snapshots = self.run_dir / "snapshots"
        self.snapshots.mkdir(parents=True, exist_ok=True)
        self.file = (self.run_dir / "events.jsonl").open("w")
        self.cycle = 0
        self.counter = 0
        self.current = None
        self.evidence_level = evidence_level
        self.restores = []
        self.expansions = 0
        self.written = set()

    def emit(self, stage, **fields):
        row = dict(run_id=self.run_dir.name, episode_id=0, planning_cycle_id=self.cycle,
                   evidence_level=self.evidence_level, hypothesis_id="rss_history_merge", event_stage=stage)
        row.update(fields)
        self.file.write(json.dumps(snapshot(row), sort_keys=True, allow_nan=False) + "\n")

    def history(self, value):
        if value is None:
            return None
        raw = json.dumps(snapshot(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        if digest not in self.written:
            (self.snapshots / (digest + ".json")).write_text(raw + "\n")
            self.written.add(digest)
        return {"digest": digest, "ref": "snapshots/" + digest + ".json"}

    def node(self, node):
        if node is None:
            return None
        return dict(candidate_id=getattr(node, "_spais_id", None),
                    parent_id=getattr(node.parent, "_spais_id", None),
                    state_exact=dict(p=node.p, l=node.l, t=node.t, v=node.v),
                    cost_to_come=node.cost2come, cost_to_go=node.cost2go, cost=node.cost)

    def wrap(self, cls, name, fn):
        original = getattr(cls, name)
        self.restores.append((cls, name, original))
        setattr(cls, name, fn(original))

    def install(self, Node, Vertex, AStar, ISpace, StateChecker):
        trace = self

        def ctor(original):
            def wrapped(node, *args, **kw):
                original(node, *args, **kw)
                trace.counter += 1
                node._spais_id = trace.counter
                trace.emit("candidate_generated", node=trace.node(node))
            return wrapped
        self.wrap(Node, "__init__", ctor)

        def assign_history(original):
            def wrapped(node, history):
                result = original(node, history)
                trace.emit("history_assigned", node=trace.node(node), history=trace.history(history),
                           history_origin="observed" if node.parent is None else "predicted_from_planner_branch")
                return result
            return wrapped
        self.wrap(Node, "add_predict_shadow", assign_history)

        def merge(original):
            def wrapped(vertex, node):
                idx_t, idx_v, idx = vertex.get_idx(node.t, node.v)
                retained = vertex.node_list[idx]
                fields = dict(node=trace.node(node), retained=trace.node(retained),
                              lattice_key=dict(p=vertex.p, l=vertex.l, t_bin=idx_t, v_bin=idx_v),
                              parent_history=trace.history(getattr(node.parent, "predicted_shadows", None)),
                              retained_parent_history=trace.history(getattr(getattr(retained, "parent", None), "predicted_shadows", None)),
                              history_origin="predicted_branch_parent_or_observed_root",
                              candidate_prediction_computed=node.predicted_shadows is not None)
                try:
                    accepted = original(vertex, node)
                except Exception as exc:
                    trace.emit("merge_exception", event_reason=type(exc).__name__ + ": " + str(exc), **fields)
                    raise
                trace.emit("merge", accepted=accepted,
                           event_reason=getattr(node, "_spais_accept_reason", "empty_slot" if retained is None else "existing_candidate_cost"), **fields)
                return accepted
            return wrapped
        self.wrap(Vertex, "add_node", merge)

        def prediction(original):
            def wrapped(space, *args, **kw):
                result = original(space, *args, **kw)
                trace.emit("prediction", t_predict=args[0], history_origin="predicted_from_planner_branch",
                           history=trace.history(result[1]))
                return result
            return wrapped
        self.wrap(ISpace, "predict", prediction)

        def observation(original):
            def wrapped(space, *args, **kw):
                result = original(space, *args, **kw)
                trace.emit("observation_update", sim_time=args[0], history_origin="observed", history=trace.history(result[1]))
                return result
            return wrapped
        self.wrap(ISpace, "update", observation)

        def expansion(original):
            def wrapped(planner, node, *args, **kw):
                if getattr(planner, "_spais_expansion_budget_remaining", 1) == 0:
                    trace.emit("expansion_budget_stop", node=trace.node(node))
                    return original(planner, node, *args, **kw)
                previous = trace.current
                trace.current = node
                trace.expansions += 1
                trace.emit("expansion", node=trace.node(node), history=trace.history(node.predicted_shadows))
                try:
                    return original(planner, node, *args, **kw)
                finally:
                    trace.current = previous
            return wrapped
        for name in ("expand_node", "expand_node_openloop"):
            self.wrap(AStar, name, expansion)

        def safety(original):
            def wrapped(checker, *args, **kw):
                result = original(checker, *args, **kw)
                trace.emit("safety_check", parent=trace.node(trace.current),
                           state_and_times=list(args[:6]), safety_pass=result[0],
                           cross_cost=result[1], opposite_cost=result[2],
                           use_record=kw.get("use_record"), safety_reason_code="unresolved")
                return result
            return wrapped
        self.wrap(StateChecker, "is_safe_plan", safety)

        def plan(original):
            def wrapped(planner, *args, **kw):
                trace.cycle += 1
                trace.expansions = 0
                start = time.monotonic()
                from rss_checkpoint import capture
                checkpoint = capture(planner, args, trace.run_dir, trace.cycle, original.__name__)
                trace.emit("planning_start", method=original.__name__, inputs=list(args[:5]), checkpoint=checkpoint)
                try:
                    result = original(planner, *args, **kw)
                except Exception as exc:
                    trace.emit("planning_exception", error=type(exc).__name__ + ": " + str(exc))
                    raise
                else:
                    path = []
                    node = planner.goal_node
                    while node is not None:
                        path.append(trace.node(node))
                        node = node.parent
                    trace.emit("planning_end", selected_path=list(reversed(path)), used_expansions=trace.expansions,
                               used_wall_ms=1000 * (time.monotonic() - start),
                               termination_reason=getattr(planner, "_spais_stop_reason", None) or ("goal_or_horizon" if path else "frontier_exhausted"))
                    trace.file.flush()
                    return result
            return wrapped
        for name in ("plan", "plan_openloop"):
            self.wrap(AStar, name, plan)

    def close(self):
        for cls, name, original in reversed(self.restores):
            setattr(cls, name, original)
        self.file.close()
