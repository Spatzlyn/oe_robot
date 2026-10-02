# Public-package validation

The public renderer/native runner was executed with the repository's native
wrapper and a newly installed CPython 3.7 environment using the public
dependency setup. The inherited `PYTHONPATH` was unset. No GPU or simulator
server was used.

| Fresh replay | Native sequences | Native updates | Result |
|---|---:|---:|---|
| 640×360 Original + single admission, traced/plain | 4 | 36 | 76/76 checks passed |
| 1920×1080 Original + single admission, traced/plain | 4 | 36 | 76/76 checks passed |

Each replay checks regenerated full depth arrays, camera transforms, geometry,
all complete outputs, every recorded event and visibility query, method and
instrumentation source, traced/plain equality, exact target application,
identical execution before intervention, and independent body feasibility.
The expected omission times and local recovery match the historical results.
Raw public validation outputs are in `replay_validation/sensor640_fresh/` and
`replay_validation/sensor1920_fresh/`.

The offline saved-record check passed 345/345 checks across all 17 historical
traced sequences and their 17 plain counterparts (306 historical native
updates). Its optional independent per-pixel body insertion check was executed
at both resolutions and matched the historical zero-depth-change records.
See `offline_validation/`; this is offline reanalysis, not another native run.

## Preserved initial verifier failure

`replay_validation/sensor640/` retains the first portability attempt. All four
native sequences completed and the stored JSON outputs matched the historical
JSON exactly, but two event-comparison assertions failed. The verifier had
compared live Python tuples in event keys against JSON lists from the saved
record. The correction compares both in the serialized JSON schema. It does
not alter event contents/order, native code, method behavior, sensor inputs,
or judgments of witness feasibility.

`replay_validation/first_attempt_source.py` preserves the exact initial runner
matching that attempt's harness hash; it is an archival source snapshot, not
an entry point. The fresh 640 replay was repeated after this verifier-only
correction and in the newly installed environment. No failed native execution
or scientific negative was removed. The initial 4 completed sequences add
36 updates to the public-package execution denominator: **12 sequences / 108
updates in this packaging task**, of which 8 sequences / 72 updates are the
successful clean-environment reproductions. They reproduce two previously
seen resolution conditions, not new independent scenes.

The separate historical `confirmation_v2` failure occurred before native
execution because a passive-logger regex did not match. It remains in
`expected/confirmation_v2/` and is not merged with the portability failure.

## Figure extraction

`figure1/build_figure.py` passed 93 checks and exported both requested figures.
The main PNG was visually reviewed for readable labels, complete output union
and distinct witness styling. This extraction executes no native updates.
Figure source inputs use regenerated public hashes following path sanitation.

## Changes and limits

Portability changes: repository-relative imports, explicit resolution/output
CLI, input/source checks, privacy-preserving manifest fields, and the JSON
comparison correction above. The fixed renderer, manager boundary, native
update logic, local intervention target and witness geometry are preserved.
The optional all-control CLI uses the existing instrumented implementations;
this packaging task freshly reran Original/single pairs and audited saved
controls, without repeating the historical sweep or its timing benchmark.

No new same-scene checker query, collision measurement, completion experiment,
natural frequency estimate, or held-out generalization result was produced.
