# Native reproduction

These commands execute the pinned implementation on the paper's controlled inputs. They are distinct from the lightweight saved-record audit in `artifact/`. They use CPU only, require the native environment, and never connect to a running simulator.

From the repository root, first follow `environment/README.md`. Every output directory must be new. The launcher will not overwrite an existing run.

```bash
bash environment/run_native.sh reproduce/run.py controlled --output results/controlled
python reproduce/verify_outputs.py controlled --output results/controlled
bash environment/run_native.sh reproduce/run.py checker-near --output results/checker-near
python reproduce/verify_outputs.py checker-near --output results/checker-near
bash environment/run_native.sh reproduce/run.py checker-far --output results/checker-far
python reproduce/verify_outputs.py checker-far --output results/checker-far
```

The checker defaults to the byte-identical archived controlled-state pickles in `fixtures/controlled/`. To connect it to your regenerated controlled state, add `--small-run results/controlled` to either checker command. This is still the **separate fixed checker fixture**, not a checker run on the synthetic-depth sensor sequence.

For each experiment below, run:

```bash
bash environment/run_native.sh reproduce/run.py EXPERIMENT --output results/EXPERIMENT
python reproduce/verify_outputs.py EXPERIMENT --output results/EXPERIMENT
```

| EXPERIMENT | Main output | Expected result and denominator |
|---|---|---|
| `controlled` | `summary.json`, `witness.json`, `reference.pkl`, `implementation_states.pkl`, per-case epoch files | Seven existing fixture settings × four methods = 28 runs. In the connected base fixture at t=4 s, Original omits all 293 finite hypotheses; single admission, structural key and mature guard preserve the tested target. The 293 are hypotheses at one epoch, not episodes. |
| `controlled-trace` | `events.json`, `summary.json` | Nine updates. Records the same-update admission history and the targeted rejection; the representative controlled fixture's short job has no mature output. This last property is not required by the mechanism and does not describe the 1920-pixel sensor example. |
| `controlled-controls` | `full_state_coverage.json`, `summary.json`, per-control records | 189 position-speed checks (7 × 3 × 9), five site ablations, nine additional fixture/method controls, history-unit comparison, reachable danger-zone witnesses. Keeps the separate early velocity-envelope discrepancy. |
| `controlled-audit` | `observation_equivalence.json`, `geometry_audit.json` | Analytic interval-erosion check for the controlled observation pair, and 32 stored checker geometry comparisons. Uses archived control/checker records; it does not rerun the checker or establish sensor-scene observation equivalence. |
| `checker-near` | `results.json`, `summary.json` | The same 18 candidates in each of five arms. Original allows 18; single admission, structural key, mature guard and the finite-reference arm allow 4. These are permission differences, not collisions. |
| `checker-far` | `results.json`, `summary.json` | Five × 18 checks; every arm allows 18. This control changes the longitudinal offset by 100 m **and removes the background lane-135 component**. It is not a one-factor distance ablation. |
| `repairs` | `runs.jsonl`, `execution_schedule.json`, `summary.json`, `warmups.json`, generated interventions | 7 fixture settings + 4 duplicate-workload settings × 5 methods × (11 timing + 1 instrumentation + 1 memory repetition) = 715 recorded runs; five warmups are separate. Historical replay completed all 715. |
| `pruning-development` | `development/results.json`, event records | Constructed subset-fork input × five methods. Original, structural key and admission-OFF omit the branch witness; mature guard and all-backward-reductions-OFF preserve it. This is a constructed mature-output case, not the admission example. |
| `pruning-validation` | `validation/results.json`, event records | Five previously fixed structural conditions × five methods = 25 rows, including alternate-owner, order, and implicit-tail controls. Historical “validation” is replayed, not new held-out evidence. The implicit-tail case remains unresolved. |
| `pruning-mature-only` | `mature_only_ablation/D1_subset_fork__mature_only_off.json` | One constructed case with only the mature-output predicate disabled; the witness is retained. |
| `native-search` | `development_schedule.json`, `development_summary.json`, `development/*.json` | All 256 predefined development schedules; 256 completed. This is synthetic topology and prescribed visibility with native genesis/predict/update, not a sensor-realized occurrence study. Historical `positive_epochs` are the original narrow mature-only endpoint, not a general causality label. Use the corrected offline v3 audit for 2 cause-attributed versus 102 unresolved witness-times. |
| `native-attribution` | `representative_attribution/summary.json`, four traces | Original, admission-only-OFF, visited-only-OFF and mature-only-OFF on one fixed representative at t=0.25 s. Prefix and target-input parity hold. Only visited-only-OFF retains the two target witnesses; this is separate from constructed mature-output D1 and from admission C1. |
| `native-wrapper` | `summary.json`, two full traces | Two representative schedules × five native `update_visibility` calls = ten updates. All post-update forests match the archived generated-input records; the wrapper's initial inbound is 17.5 m on a legal waypoint. |

## Inputs and changes

- `fixtures/controlled/`: exact rational-reference and native-state pickles.
- `fixtures/checker/`: recorded pair context, checkpoint, and OpenDRIVE geometry. `Town01.xodr` must remain beside `cycle_0005.pkl`.
- `fixtures/map/`: deterministic gzip of the reconstructed OctoMap. The launcher verifies compressed and decompressed SHA-256 before caching it in `.cache/native_fixtures/`. There is no empty-map fallback.
- `fixtures/audit/`: the stored near/far checker, control and trace records used by the ancillary audit.
- `fixtures/pruning/`: the two complete archived representative traces used by attribution and wrapper checks.
- `_common/`: fixture, rational reference, output decoder, existing mature guard, and unchanged checker-restore/measurement helpers.
- `portability_changes.json`: original relative source paths and original/public hashes. Paths, output placement, vendor revision reporting and package manifests were adapted. Native scientific bodies, candidate values, visibility schedules and intervention conditions were not changed.

The native search's local `support()` logic explicitly handles terminal inbound nodes. Do not replace it with an unsupported generic decoder or treat any serialization difference as a witness omission.

The existing measurement helper uses an explicit empty `GeometryCollection` where older near-checker records stored an empty `Polygon`. `verify_outputs.py` canonicalizes **only empty geometry** and exactly equal integral numeric values; nonempty geometry and verdicts remain in the comparison. Newly generated summaries also state the near control's zero offset/background-retention flags explicitly. Timing, Python-allocation values and traced wall times vary by host and are excluded from expected scientific-output fingerprints.

## Timing and interpretation

Repair timing covers the native update call, including guard lookup and primitive work. It excludes imports, manager construction, prediction, input deep copies, queue filling, serialization and offline coverage tests. Input preparation and offline checking are recorded separately. Memory is additional Python-traced allocation during update, not full-process or native-allocator memory. No real-time deadline or inevitable safety/efficiency tradeoff is claimed.

All searched/visited state in the admission example is initialized per update. Later regeneration does not cancel an earlier omission. The finite-reference arm is an independent underapproximation and not a universal safety oracle. Permission changes are not observations of physical collision, inevitable collision, or task completion. Synthetic-depth reproduction is documented separately in `sensor/`.

`verification.json` records the packaging replay checks. Controlled reference/native-state pickles regenerated byte-for-byte; all checker verdicts matched; all 256 search records matched; full repair and constructed-boundary replays preserved their semantic outputs. Fresh environment tests additionally reran the controlled experiment and near checker. One first import attempt failed because the headless setting was absent, before any experiment ran; the launcher now sets it. This was an environment repair, not a scientific intervention.

The separate velocity-envelope diagnostic is optional: see [ancillary scope](../ancillary/README.md). The `controlled-audit` command produces the paper-facing observation and geometry records; `ancillary-audit` additionally produces the preserved velocity record.
