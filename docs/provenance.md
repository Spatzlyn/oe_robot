# Provenance, transformations and validation scope

## Source identity

The analyzed implementation is SafeRoboticsLab/Safe_Occlusion_Aware_Planning, revision `2b6b06637850b406cfbeab926a3dedc01edad91e`. [upstream_files.json](upstream_files.json) records upstream and distributed SHA256 for every vendored file. Required runtime and third-party build sources are bundled; unused maps, simulator assets, compiled caches and unrelated research were omitted.

The four pre-existing compatibility changes are isolated in [compatibility.patch](../environment/compatibility.patch): headless Matplotlib backend selection, Traffic Manager port handling, and sensor-ready frame metadata. The core shadow propagation, reachable-set and safety-checker modules are unchanged. The CPU experiment entry points do not start a simulator or use the live sensor callbacks.

## Public-copy transformations

Original private records are retained outside this repository. The public copy removes submission-author identifying paths and private Drive URLs. It does not remove upstream copyright attribution.

The offline archive keeps 647 members. Of these, 619 are byte-identical to their originals; 28 contain identity-text or derived source-hash metadata transformations. Independent comparison preserved JSON structure and 4,907,816 non-string scalar values, including 3,773,805 numerical scalars. All 13 NPZ files in that archive are byte-identical. See [PUBLIC_COPY_VERIFICATION.json](../artifact/PUBLIC_COPY_VERIFICATION.json) and [ANONYMIZATION.json](../artifact/ANONYMIZATION.json).

Public hashes refer to the bytes actually distributed. Historical hashes are explicitly named and retained when needed for source lineage. A public source hash must not be silently interpreted as the old private-file hash.

The native checker's four required pickle fixtures are copied byte-for-byte; their string opcodes were inspected without executing them during the identity audit. Runtime wrappers load only these provided fixtures. The reconstructed occupancy map is losslessly gzip-compressed with a deterministic header; both compressed and original byte hashes are provided.

## Compatibility, instrumentation and scientific intervention

| Change class | Examples | What is held fixed |
|---|---|---|
| Portability / packaging | Relative root discovery, explicit output arguments, import bootstrap, anonymous paths, compressed map | Recorded scene/model, candidate tuples, observation schedules and scientific method |
| Instrumentation / verification | Whole-output decoder, event logging, source/input checks, JSON tuple/list normalization in a verifier | Native execution and numeric inputs/outputs |
| Scientific intervention | One selected admission, structural key, restricted guard, admission-off, mature-only, visited-only, all-backward-off | The per-experiment protocol documents the exact changed decision and preserved conditions |
| Actual model/input differences | 640 versus 1920 resolution; shifted checker component and common background-lane removal | Separate conditions, never described as instrumentation-only changes |

The near-checker output instrumentation now labels an empty polygon intersection as an empty GeometryCollection in some records. Query tuples and checker verdicts are preserved; raw serialized geometry-type identity is not claimed. Near and far expected outputs are separately retained.

The first portable sensor verifier compared live tuples to archived JSON lists and falsely failed an event-history assertion. The corrected verifier normalizes through the saved JSON schema; numeric execution data did not change. The failed verification and successful new-environment replays are retained in [PORTABILITY_VALIDATION.md](../reproduce/sensor/PORTABILITY_VALIDATION.md). A headless import setup error in the native packaging process is likewise distinguished from a scientific negative result in the native verification record.

## Actual release validation

- Offline V3: 22,565 consistency checks, zero failures; a separate negative control confirmed a wrong expected value is rejected.
- Native reproduction: all 13 command families executed; [verification.json](../reproduce/verification.json) and [output_verification.json](../reproduce/output_verification.json) record comparisons and their limits. Controlled pickles were reproduced byte-identically; near/far candidate verdicts match.
- Clean environment: a new CPython 3.7.12 prefix, dependency install, source-built OctoMap and opendrive2lanelet, `pip check`, native imports, controlled and near-checker replay. This is a dependency/portability check, not a new scientific scene.
- Sensor: fresh 640 and 1920 Original/single-admission pairs passed 76 checks each in the clean environment, including complete arrays and execution traces. Saved-record pixel audit passed 345 checks.
- Figure 1: 93 extraction checks, vector PDF/SVG and PNG visual review, exact coordinates and whole-output memberships.

Native replays reuse existing conditions; they are not additional independent evidence for generalization. Runtime measurements are hardware-dependent and no equality to historical timing is required. The restricted finite reference and witness checks do not establish continuous soundness, task completion, or an RFM empirical benefit.

## Integrity and reproducibility

`MANIFEST.sha256` records all distributed payload files except itself. Run `python tools/verify_release.py` after download to check it. Family manifests additionally connect raw input, public transformation and generated outputs. Reproduction outputs should go to a new directory outside the preserved fixture and expected-result trees.

Archived source snapshots may contain old relative layouts for provenance. Use documented portable entry points instead of executing arbitrary source snapshots extracted from `evidence.zip`.
