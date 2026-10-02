# Record schemas and status semantics

Normalized records retain the archive path and source index/ordinal. Whole
returned forests are included so that the serialized evidence is not restricted
to a selected representative.

| Schema | Important fields | Interpretation |
| --- | --- | --- |
| `spais.e3.provenance.v1` | `files[].path/sha256/bytes`, archive hash, external inputs | Public-byte integrity and provenance, not validity from hashes alone |
| `spais.e3.output.v1` | `group/case/method`, index, `returned_forest`, feasibility, `whole_output_membership` | Designated position in the whole returned union; speed/history is not certified by presence |
| `spais.e3.event.v1` | source ordinal, raw event | Native predicate result and actual post-intervention rejection must be distinguished |
| `spais.e3.query.v1` | fixed input tuple, native result/verdict, fixture | Same-query permission accounting; no new collision or completion evaluation |
| `spais.e3.validation.v1` | actual/expected/pass, hashes, limits | Correspondence between archived evidence and expected regression results |

`whole_output_membership.status` is `present`, `absent`, or `unresolved`.
A point in a decoded interval is present in the position projection. A tail or
unsupported node can prevent a justified absence conclusion. An unresolved
record is not a zero-omission or soundness result. `absence_supported=false`
must not be treated as a successful preservation certificate.

Feasibility applies only to the stated observation model, dynamics and body
footprint. Native output itself is not the witness-feasibility reference. The
sensor full-body certificate applies to its fixed-panel geometry; it does not
inherit the old finite model fixture's observation-equivalence proof.

`none` indicates that the historical harness did not run that consumer query.
`not_recorded` indicates missing measurement. The legacy
`consumer_query_id=legacy_near_and_far_query_fixture` is a separately transplanted
checker fixture, not a native consumer in the sensor sequence.

Keep the following denominators separate: scene-condition, method sequence,
update, query, candidate, witness-time, repetition and offline consistency check.
The 1,410 normalized output rows are not independent episodes. The 180 query
rows are near/far x 5 arms x 18 candidates, not 180 unique action candidates.
The attribution inventory's 104 rows are witness-times, not collision events.

`t_return_model` uses the recorded model time; wall-clock return latency was not
recorded for these rows. Archived cost benchmarks have their own timing and
instrumentation scope and must not be inferred from this field.
