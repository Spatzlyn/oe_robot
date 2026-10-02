# V3 cause-attribution correction

The latest labels are produced by `validate_offline_v3.py` and are recorded in
`validation_public/native_unresolved_inventory.json`. Do not use the historical
V2 inventory as the current cause-label result.

The V1/V2 analysis attached `visited_suppression_representative` to all missing
witness-times in `D_template_000`, using its condition identifier. The recorded
intervention disabled visited suppression only at **t = 0.25**. Missing states
at later epochs do not establish the same direct cause at those later original
prefixes. In addition, the intervention may change subsequent history.

| Witness-times | Current label | Reason |
| --- | --- | --- |
| D000, t=0.25, lane 2 and lane 3: 2 rows | `visited_suppression_representative` | Same-prefix, same-target-input visited-only intervention restores both positions |
| D000, t=0.5, 0.75, 1.0, lane 2 and lane 3: 6 rows | `unresolved` | No independent local cause intervention at each later original prefix |
| Other 34 missing conditions: 96 rows | `unresolved` | No additional cause intervention was run |

The missing-state denominator is unchanged: **104 witness-times = 2 locally
adjudicated + 102 unresolved**. The 35-condition denominator remains one
condition with at least one attributed target and 34 with none. The first
condition itself contains six unresolved witness-times. It is incorrect to say
that every omission in this one condition has been explained.

V3 checks the original development prefix, target predicted input, observation
schedule, exact one-line visited intervention, and complete target outputs. A
narrow independent terminal-interval decoder confirms the target positions.
The output `attribution_scope_audit.json` records these comparisons. Presence
here concerns the designated position, not the complete speed/history semantics.

`version_parity.json` checks that exactly six cause values change relative to
the preserved public V2 baseline. The 1,410 output records, 828 event records,
180 query records, four witness definitions, heuristic records, and source
lineage are otherwise unchanged. Source hashes in both public versions refer
to the anonymized archive copies; historical private source hashes are not
misrepresented as public byte identities.

The public re-execution reports 22,565 checks, zero failed, and zero new native
runs. The correction changes attribution scope, not missing-state existence,
checker verdicts, the original C1 result, or the unresolved native D1 search.
