"""Restricted dominance guard for flat backward shadows.

This is a bounded diagnostic correction, not a network-wide correctness result.
Both a generated, already time-propagated work item and mature outputs are
compared to committed mature coverage at that SAME update time. A processed
input is NOT a coverage certificate: it may still have pending split children.
Lane-only pruning is disabled for backward shadows. Forward rules stay intact.
"""
import copy,inspect,textwrap

def dominates(retained,candidate):
    # Only this closed form has an established common history interpretation.
    a,b=retained.root,candidate.root
    if retained.risk_bound or candidate.risk_bound:return False
    if retained.parent_id!=candidate.parent_id or a.id!=b.id:return False
    if type(a).__name__!='InOutBound' or type(b).__name__!='InOutBound':return False
    if a.child_node or b.child_node:return False
    if a.ds_in!=b.ds_in or a.t_in!=b.t_in or a.t_out!=b.t_out:return False
    if a.ds_in_hist is not None or b.ds_in_hist is not None:return False
    if a.t_in_hist is not None or b.t_in_hist is not None:return False
    # Same inbound/history, same update epoch; interval coverage contains candidate.
    # Works for either lane direction without assuming the lane's sign.
    return min(a.ds_in,a.ds_out)<=min(b.ds_in,b.ds_out) and max(a.ds_in,a.ds_out)>=max(b.ds_in,b.ds_out)

def make(original, admission=True, visited=True, mature=True):
    source=textwrap.dedent(inspect.getsource(original))
    code=source
    if visited:code=code.replace('if bound_lane_id in bwd_visited_lane:', 'if False:  # no lane-only dominance certificate')
    if admission:code=code.replace('if new_shadow_begin not in bwd_searched_begin:',
        'if not any(dominates(prior, new_shadow) for prior in mature_shadow_list):')
    if mature:code=code.replace('return self._check_repeated_bwd_shadow(shadow2check, shadow_list)',
        'return any(dominates(prior, shadow2check) for _, prior in shadow_list)')
    scope=dict(original.__globals__,dominates=dominates)
    exec(compile(code,'conservative_shadow_reduction.py','exec'),scope)
    return scope['_update_shadow'],code
