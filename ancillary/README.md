# Auxiliary full-state diagnostic

The v3 paper reports designated position omissions and same-checker permissions.
A separate historical velocity-envelope discrepancy is preserved as a limit of
full-state interpretation. It is not a paper result or an attribution to C1.
The complete offline audit includes it to preserve the existing negative evidence.

The paper-facing command `controlled-audit` checks observation equivalence and
stored checker geometry. To additionally replay the auxiliary velocity analysis:

```bash
bash environment/run_native.sh reproduce/run.py ancillary-audit --output outputs/ancillary_audit
python reproduce/verify_outputs.py ancillary-audit --output outputs/ancillary_audit
```

Its `velocity_audit.json` must match the historical scientific-output fingerprint.
The saved evidence is `runs/semantic_manuscript_audit_v1/velocity_audit.json`
inside `artifact/evidence.zip`. No new scientific condition is introduced.

The full offline validator also preserves a five-case audit of shortcuts such
as checking only final output or relying on patch agreement. These are selected
counterexamples, not a detector benchmark or an additional paper contribution.

## Velocity-envelope audit: 별도 native bound discrepancy

**판정은 현재 1D model에서 native bound/footprint 처리의 별도 discrepancy입니다.** Pure decoder/coordinate shift 또는 polygon sampling 부족만으로 설명되지 않습니다. Bound와 `−3`은 수정하지 않았습니다.

| 표현 / 호출 | 위치 의미와 변환 |
|---|---|
| Reference `q` | 객체의 front; center는 `q−1.5`, rear는 `q−3`, 모두 같은 longitudinal speed를 가집니다. |
| `ds_in=15`, `ds_out=3`, depth=12 | 객체의 center가 아니라 visibility region의 upstream/downstream boundary입니다. Lane 1의 traffic coordinate는 `q=−ds`입니다. |
| `depth−3=9` | `depth<3`이면 vehicle에 너무 짧다는 source branch와 연결된 length correction입니다. Length-12 region에 length-3 object가 들어갈 때 marker가 이동할 수 있는 span은 9입니다. Observation cell boundary의 0.25 m offset과는 다른 보정입니다. |
| `bwd_shadow_FRS` | Outbound를 원점으로 하는 longitudinal position–speed envelope입니다. `dis−depth`로 inbound 측을 두고 downstream FRS boundary를 이어 붙입니다. 하나의 front/rear state 표기라고 명시돼 있지는 않으며, checker에서는 occupancy/boundary envelope로 소비됩니다. |
| `_check_intersection_bwd` | `p_rel=delta_s_from_end(shadow_ds)+processed_ds`, 이후 `translate_polygon(FRS,−p_rel)`입니다. Body center를 가리키는 알려진 object의 FRS는 `bbox.ext_x`로 확장하지만 hidden-shadow 경로에는 별도 center 보정이 없습니다. |

Lane 1에서 physical marker `q_m`의 local coordinate는 `x=q_m+ds_out`이고 checker coordinate는 `x−(ds_out+processed_ds)=q_m−processed_ds`입니다. Reference placeholder는 `ds_out=0`에 absolute traffic `q`를 넣으므로 같은 front point가 같은 checker coordinate로 갑니다. Translation은 speed를 바꾸지 않습니다. Source: [native FRS](../repos/rss_occlusion/risk_analysis/shadow_utils.py), [checker](../repos/rss_occlusion/risk_analysis/state_checker.py), [translation](../repos/rss_occlusion/risk_analysis/reachable_set.py).

Feasible trajectory는 `q(t)=−11.5+6t+2t²`, `v(t)=6+4t`, `0≤t≤1`입니다. t=0, 0.5, 1에서 `(-11.5,6) → (-8,8) → (-3.5,10)`이고 각 footprint는 prescribed hidden field에 들어갑니다. Travel 8 m는 native region의 length correction 후 span 9 m보다 작습니다. 실제 visibility-cell 경계로 계산한 admissible front span은 8.5 m이며 witness는 그 안에서도 양립합니다. 따라서 waypoint/cell 경계의 0.25 m offset으로 만든 반례도 아닙니다. Stationary witness와는 별개입니다.

Native 계산은 다음과 같습니다.

```text
delta_s = depth−3 = 9, delta_t = 1
V_in = (9 − 0.5×8×1²) / 1 = 5
V_out = sqrt(5² + 2×4×9) = sqrt(97) = 9.848857801796104
```

`t_sense=t_predict=1`이면 downstream FRS의 최대 속도도 이 cap이며, sampled inbound curve도 이를 넘지 않습니다. 실제 CPU 계산에서 n=20, 200, 2000 모두 **polygon 전체의 최고 속도**가 동일했습니다. Front local x=−0.5, center x=−2, rear x=−3.5에서 모두 v=10이 제외됐고 native horizontal translation 뒤에도 동일했습니다. Rear 위치의 낮은 bound에는 sampling 차이가 조금 있지만, 전체 cap이 10보다 낮다는 결론에는 영향이 없습니다. 따라서 front/rear/center offset으로 이 witness를 되살릴 수 없습니다.

이 판정은 코드가 사용한 parameters와 명시한 initial/observation/dynamics model에 대한 것입니다. 원문의 일반 theorem이나 원 map의 safety violation을 주장하지 않으며, undocumented policy constraint의 의도를 역추정하지 않습니다. Bound 수정은 이 artifact의 범위 밖입니다. 원자료는 위 ZIP 경로에 있습니다.

