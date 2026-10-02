"""Diagnostic intervention: include shadow-root graph in backward worklist key.

This is not a validated production fix. Original node merge, safety, dynamics,
visibility and all remaining shadow pruning rules are preserved.
"""
import inspect
import textwrap
from audit_rss_continuations import digest

def install():
    from risk_analysis.shadow_utils import ShadowUtils
    original=ShadowUtils._update_shadow
    code=textwrap.dedent(inspect.getsource(original))
    first='new_shadow_begin = (new_shadow.root.id, new_shadow.root.ds_out)'
    second='bwd_searched_begin.append((cur_shadow.root.id, cur_shadow.root.ds_out))'
    assert code.count(first)==2 and code.count(second)==1
    patched=code.replace(first,'new_shadow_begin = worklist_key(new_shadow)').replace(second,'bwd_searched_begin.append(worklist_key(cur_shadow))')
    context=dict(original.__globals__)
    context['worklist_key']=lambda sh:(sh.root.id,sh.root.ds_out,digest(sh.root))
    exec(compile(patched,'structural_shadow_key.py','exec'),context)
    ShadowUtils._update_shadow=context['_update_shadow']
    return patched
