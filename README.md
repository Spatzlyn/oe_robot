# Possible Hazards Lost Before Safety Checks

**A Case Study in Occlusion-Aware Planning — anonymous research artifact**

This repository provides code, fixed inputs, saved results and independent checks for a case study of feasible hidden-object positions omitted by an occlusion-aware planner. It includes a controlled trajectory reference, a single-admission causal intervention, a separate safety-checker comparison, synthetic-depth reproduction, simple repairs, and pruning-stage controls.

Start with the saved-results validator. Native replays are separate commands and execute the analyzed implementation again.

## Quick start: verify the reported evidence

Python 3.10 or later, standard library only; no simulator, GPU or native dependency installation:

```bash
python artifact/validate_offline_v3.py \
  --artifact artifact \
  --output /tmp/oe_robot_offline_check
```

Expected: **22,563 checks, 0 failures**, 1,410 normalized output records and 180 checker-query records. The corrected native-search attribution is **2 confirmed witness-times and 102 unresolved witness-times**. Output is written to a new directory; existing output directories are not overwritten.

This full audit includes the explicitly labeled auxiliary velocity diagnostic as well as the paper evidence. It checks archived inputs, source lineage, whole-output position membership, query records and consistency assertions. It **does not rerun the native safety checker, renderer, or planner**. See [artifact/README.md](artifact/README.md) and [the v3 label correction](artifact/LABEL_CORRECTION.md). The retained v2 records are a comparison baseline required by v3, not the current attribution.

## Reproduce the paper's results

Install the [native environment](environment/README.md) for commands using `run_native.sh`. All listed native experiments run on CPU without starting a CARLA server. Use a fresh output directory for each command.

| Paper result | Command / entry point | Output and expected interpretation |
|---|---|---|
| Controlled witness and independent finite reference (§3.3, §4) | `bash environment/run_native.sh reproduce/run.py controlled --output outputs/controlled` | Feasible stationary front position 8 m; Original omission at 3, 3.5 and 4 s; 293 finite reference hypotheses at 4 s. Observation modification and simple repairs are distinct arms. |
| One admission after an identical prefix | `bash environment/run_native.sh reproduce/run.py controlled-trace --output outputs/controlled_trace` | Short job records the key; larger job is rejected; one admission restores the witness. |
| Observation equivalence and auxiliary controls | `reproduce/run.py controlled-controls` and `controlled-audit` under the same native launcher, each with `--output NEW_DIR` | Finite-reference/trajectory, observation-equivalence and stored checker-geometry checks. |
| Table 1, original location | `bash environment/run_native.sh reproduce/run.py checker-near --output outputs/checker_near` | Same 18 query tuples: Original 18/18; reference, single admission, structural key and restricted guard 4/18. |
| Table 1, upstream control | `bash environment/run_native.sh reproduce/run.py checker-far --output outputs/checker_far` | All methods 18/18. This archived control also removes the same background lane representation from every arm; see the detailed reproduction guide. |
| Figure 1 and separate 4 s snapshot | `python figure1/build_figure.py --out outputs/figure1` | PDF/SVG/PNG, coordinates, whole-output union, membership and 93 extraction assertions; reads saved 1920×1080 data. |
| Synthetic depth, both resolutions | [reproduce/sensor/README.md](reproduce/sensor/README.md) | Rerender fixed observations, run Original and one admission, compare complete outputs and identical prefixes; also retain all historical controls and failures. |
| Four repairs and measured cost | `bash environment/run_native.sh reproduce/run.py repairs --output outputs/repairs` | Seven controlled configurations plus the archived duplicate-work stress schedule; coverage, completion, timing, queue and memory are reported separately. Runtime values are machine dependent. |
| Constructed later-pruning counterexample and controls | `reproduce/run.py pruning-development`, `pruning-validation`, `pruning-mature-only` under the native launcher | Distinguishes admission repair, completed-output pruning and alternate-owner coverage. These are constructed inputs. |
| Native initialized search and cause limits | `reproduce/run.py native-search`, `native-attribution`, `native-wrapper` under the native launcher | Fixed 256-condition development schedule; 41 branch-set inclusions; no confirmed designated-witness loss at completed-output pruning; visited-only attribution and two wrapper controls are separate results. |

The [detailed reproduction guide](docs/reproduction.md) gives complete commands, files, expected values, measured denominators and verification status. It distinguishes new execution from recomputation of saved data. [Provenance](docs/provenance.md) records portability changes and hashes.

## Installation and data

- **Offline validation:** Python standard library; see above.
- **Figures:** a modern NumPy/Matplotlib environment, specified in `environment/figure-requirements.txt`.
- **Native replay:** Linux x86_64, CPython 3.7.12 and pinned dependencies. `bash environment/setup_native.sh` builds the modified OctoMap binding from source. See [environment/README.md](environment/README.md).
- **Inputs:** all fixed inputs needed for these commands are included. The reconstructed map is compressed below GitHub's single-file limit, verified on decompression, and cached under `.cache/`. No personal download link is required.
- **Fresh results:** write to `outputs/` or an external new directory. Archived reference results are kept separately. Do not overwrite them to make a check pass.

## Reading the results

The sensor sequence, controlled road fixture and safety-checker intersection fixture are separate experiments. The checker uses controlled outputs in a saved scenario; it is not an end-to-end checker evaluation of the sensor scene. **14 changed permissions are not collisions, and 293 hypotheses are not episodes.** No vehicle action is executed by the checker comparisons.

Position absence establishes omission of the corresponding feasible state, but finite position coverage does not prove continuous safety or full planner soundness. A later regenerated output does not undo an earlier omission. The processing records reset at each update; the central case is not a cross-epoch stale cache. A short retained output exists in the 1920×1080 case, so `mature=None` is not necessary.

Simple repairs suffice for the tested admission-related omissions at small measured cost. The constructed output-pruning case, visited-lane finding, and unresolved search records are retained with their distinct scopes. An [auxiliary full-state diagnostic](ancillary/README.md) is preserved separately and is not a reported v3 paper result. This artifact does not claim a new general preservation principle or direct RFM experimental validation.

## Upstream implementation

We analyze [Safe Occlusion-Aware Autonomous Driving via Game-Theoretic Active Perception](https://github.com/SafeRoboticsLab/Safe_Occlusion_Aware_Planning), RSS 2021, revision `2b6b06637850b406cfbeab926a3dedc01edad91e`. Required source, licenses and file hashes are included. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Names in third-party copyright notices identify upstream authors and are intentionally preserved. Public artifact paths, archive contents and generated metadata are checked separately for identifying information belonging to this submission.
