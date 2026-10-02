# Paper-to-artifact reproduction guide

Commands below run from the repository root. Every `outputs/...` destination must be new. Installation is in [environment/README.md](../environment/README.md). The native launcher is CPU-only and does not start a simulator.

## 1. Fast saved-data audit

```bash
python artifact/validate_offline_v3.py --artifact artifact --output outputs/offline
```

Expected terminal accounting: 22,565 consistency checks; zero failed; 1,410 normalized outputs; 180 checker query records. The 651-member evidence archive preserves failures, negative results and unresolved cases. V3 attribution is 2 confirmed witness-times and 102 unresolved. These are selected witness-times, not independent episodes.

This mode reads and rechecks archived results. It does not produce new native results. The archive contains historical source snapshots for audit; executable portable entry points are the scripts below.

## 2. Controlled experiment (§3.3 and first §4 paragraph)

```bash
bash environment/run_native.sh reproduce/run.py controlled --output outputs/controlled
bash environment/run_native.sh reproduce/run.py controlled-trace --output outputs/controlled_trace
bash environment/run_native.sh reproduce/run.py controlled-controls --output outputs/controlled_controls
bash environment/run_native.sh reproduce/run.py controlled-audit --output outputs/controlled_audit
```

The finite independent reference starts from 496 valid position–speed states and uses rational arithmetic with the recorded acceleration grid. In the main condition, the stationary body has front 8 m and footprint [8,11] m. Original misses it at 3, 3.5 and 4 seconds; at 4 seconds all 293 surviving finite reference positions are outside the output. The one-query observation modification is proved not to exclude a feasible 3 m body in the isolated 0.5 m interval. The local trace distinguishes a single admission decision from whole-sequence repair modes.

The controlled runner returns seven configurations across its existing method arms. The repairs runner below includes Original plus all four repairs. Do not combine repeated fixture replays into an occurrence rate or describe seed/serialization changes as independent scenes.

## 3. Native safety checker (Table 1)

```bash
bash environment/run_native.sh reproduce/run.py checker-near --output outputs/checker_near
bash environment/run_native.sh reproduce/run.py checker-far --output outputs/checker_far
```

Optional: replace archived controlled inputs with the controlled replay above:

```bash
bash environment/run_native.sh reproduce/run.py checker-near \
  --small-run outputs/controlled --output outputs/checker_near_regenerated
```

Five arms each evaluate the same 18 candidate tuples. Near-condition counts in order Original / structural key / restricted guard / single admission / independent reference are 18 / 4 / 4 / 4 / 4. The 100 m upstream control gives 18 in every arm. Inspect `summary.json` and `results.json`, including individual candidate verdicts and query context.

The map, saved planning cycle, pair context and controlled pickles are included under `fixtures/`. The map is decompressed to `.cache/native_fixtures/` only after checking its compressed hash; its full byte hash is checked again before consumption. No missing/empty map fallback is allowed. The saved pickle inputs should be treated as code-bearing Python serialization and only loaded from this trusted, hash-verified package.

The upstream control shifts the hidden component and removes background lane 135 from every arm. It is not a single-factor distance ablation. Near/far comparisons use their respective fixed contexts, and all candidate tuples remain fixed within a column. The historical near serialization records an empty Polygon while the current portable instrumentation may serialize it as an empty GeometryCollection; checker verdict and candidate parity are evaluated separately from that empty-geometry label.

No action is physically executed. Permission differences are not collisions, unavoidable accidents or task completion changes. The synthetic sensor scene is separate.

## 4. Sensor existence example and Figure 1

```bash
bash environment/run_native.sh reproduce/sensor/run_sensor.py --resolution 640 --output outputs/sensor640
bash environment/run_native.sh reproduce/sensor/run_sensor.py --resolution 1920 --output outputs/sensor1920
python reproduce/sensor/verify_saved.py --pixel-check --output outputs/sensor_saved_pixel_audit
python figure1/build_figure.py --out outputs/figure1
```

The first two commands independently render full depth arrays at nine epochs in four camera directions, then execute Original and single-admission native updates, each traced and plain. Each resolution executes four sequences / 36 updates. The portability validation passed 76 checks for each resolution with exact saved depth/pose, whole-output, event and query parity. The saved-record pixel audit passed 345 checks, and Figure 1 extraction passed 93.

Expected sensor memberships:

| Resolution | Original omission times | Single admission |
|---|---|---|
| 640×360 | 2.0, 3.5, 4.0 s | Restores at 2.0 s; later omissions at 3.5 and 4.0 s remain |
| 1920×1080 | 3.5 s | Restores at 3.5 s; all nine stored memberships present |

The selected 1920 scene retains a short mature output before the long job is rejected. Original covers the witness again at 4 s after a new observation. Both facts delimit the causal claim rather than erase the omission.

Historical data include nine development conditions, selected controls and the paired replay: 17 traced plus 17 plain sequences, 306 updates, with overlapping conditions. One failed pre-native instrumentation attempt is kept separately. See [sensor documentation](../reproduce/sensor/README.md) for all existing controls and [Figure 1 documentation](../figure1/README.md) for exact coordinates, prefix hashes and editable formats.

## 5. Simple repairs and observed cost (§3.4, §4)

```bash
bash environment/run_native.sh reproduce/run.py repairs --output outputs/repairs
```

This executes the archived schedule, including seven controlled configurations and duplicate-input stress cases, for five methods: Original, structural key, restricted guard, admission-off and all-backward-off. The schedule comprises 55 method–case groups, each with 11 timing repetitions, one queue-instrumented repetition, and one separately measured memory repetition: 715 completed runs. Warmups are separate.

Coverage, unresolved semantics, processing completion, time, queue size and additional traced Python allocation are distinct measures. Historical controlled-fixture medians for nine updates are approximately 1.37 ms Original and 1.81 ms admission-off. They exclude prediction, preparation and independent reference evaluation and are not a realtime guarantee. New machine timings should not be asserted equal to the saved medians. The guard lookup itself is included in update time.

All four repairs eliminate the targeted final-time position omission across the seven recorded configurations. This supports their sufficiency for those cases, not a need for a more complex algorithm or universal soundness.

## 6. Completed-output pruning and native generation limits

```bash
bash environment/run_native.sh reproduce/run.py pruning-development --output outputs/pruning_development
bash environment/run_native.sh reproduce/run.py pruning-validation --output outputs/pruning_validation
bash environment/run_native.sh reproduce/run.py pruning-mature-only --output outputs/pruning_mature_only
bash environment/run_native.sh reproduce/run.py native-search --output outputs/native_search
bash environment/run_native.sh reproduce/run.py native-attribution --output outputs/native_attribution
bash environment/run_native.sh reproduce/run.py native-wrapper --output outputs/native_wrapper
```

The constructed two-shadow counterexample is a function-input experiment: a representative covers one branch while the rejected candidate additionally covers the witness branch. Admission repairs do not recover this case; a completed-output-only ablation does. Alternate-owner controls show why candidate removal alone is not sufficient evidence of harmful omission.

The native search is a **fixed 256-condition development schedule**, five updates each, initialized with constructed shadows. Forty-one conditions contain the recorded branch-set inclusion relation; none confirms the designated witness loss at completed-output pruning. Thirty-five conditions have some missing designated positions, totaling 104 witness-times. Local attribution is established for two witness-times by disabling visited-lane pruning; the other 102 are unresolved. Do not relabel them as completed-output failures or treat zero confirmed cases as proof of impossibility.

Two representative conditions additionally check initialization from valid vehicle positions; those checks are not a guarantee that every searched constructed state is wrapper-reachable. The commands preserve the previous development/validation labels but the portability replays are regression checks, not newly held-out experiments.

## Failure reporting and verification scope

Existing scientific negatives and unresolved outcomes are retained. Packaging failures, such as a missing headless import setting or a tuple/list representation mismatch in a verifier, are recorded separately from scientific method outcomes. The sensor portability report preserves its initial failed verification even though the native numeric outputs matched.

The shipped expected results are regression expectations derived from prior evidence. They are not prospective predictions for new scenes. A passing checksum, replay, or finite witness audit does not prove full continuous safety, physically observed collision avoidance, or a direct RFM benefit.
