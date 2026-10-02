# Release review

This review checks the public package, not the identity settings of an external
hosting service. It is separate from the experiment implementations and did not
modify their frozen files or run further native experiments.

## Identity and packaging inspection

An initial read-only snapshot contained 664 distributed files. Inspection
included 35 archive/compressed containers and their nested payloads (ZIP, CARLA
egg, NPZ and gzip), plus the strings and opcodes of four pickle fixtures without
executing them. A later snapshot contained 675 files: the 11 added documentation,
manifest and verification files were checked separately; all previously inspected
payload hashes were unchanged. These are audit snapshots, not a final release
file count. The final `MANIFEST.sha256` defines the committed payload.

Two subsequent packaging-only edits were also inspected before this audit was
frozen: `environment/figure-requirements.txt` pins Matplotlib 3.10.8, matching
the version in the actual figure extraction manifest, and `.gitignore` additionally
excludes `results/`. These edits do not change the frozen scientific inputs,
experiment implementations, generated figures or validation results.

No submission-author identifying strings, private Drive links, or recognized
credential forms were found in the inspected payload. A separate direct text
scan also reported zero identifying matches. This is a targeted content audit,
not a proof that an arbitrary account, repository history, or hosting service is
anonymous.

Fifteen absolute build-path matches occur inside the unmodified official CARLA
binary. They are upstream `/home/jenkins/...` build metadata, not paths belonging
to this submission. Email-like matches were reviewed as upstream attribution
and the Python matrix expression `local@pose.matrix`. Upstream copyright,
license and contact notices were preserved deliberately.

The decompressed map cache, bytecode caches, authentication files and private
audit scripts are not release inputs. `.cache/`, `__pycache__/` and bytecode are
excluded; the map is distributed in its verified compressed form. No included
payload in the inspected snapshot exceeds GitHub's 100 MB single-file limit.

All project-authored Markdown file links resolved at the later snapshot.
Three inherited upstream README links are nonfunctional: two optional example
images and an Octovis link spelling `LICENSE` where the supplied file is
`LICENCE`. The actual license file is present; Octovis is disabled by the native
installer. These documentation links do not affect the reproduction commands.

## Numerical and claim review

The paper, root reproduction guide and family validation records were checked
together. The audit retained these distinctions:

- The sensor scene and the fixed checker intersection are separate experiments.
  Eighteen-to-four allowed candidates means 14 permission differences, not
  collisions. The far control also removes common background lane 135; it is
  not a one-factor distance ablation.
- Figure 1's original 3.5 s output covers lane-1 positions `[0,2]`, the local
  single-admission output covers `[0,13.5]`, and Original at 4 s covers `[0,13]`.
  Every panel also retains lane-999 output. A separate interval calculation
  checked the whole forests, seven identical prior epochs, the target input,
  482 identical prefix events, the single grant and the surviving short mature
  output: 46 review checks, zero failures. The independent fixed-panel body
  certificate was also rechecked. This calculation executed no native update.
- The 293 final reference hypotheses belong to one finite model epoch, not
  independent episodes or a continuous safety certificate. Later recovery does
  not cancel an earlier omission. The processing records reset per update.
- Native-search attribution is exactly two locally adjudicated witness-times
  and 102 unresolved witness-times. The constructed output-pruning counterexample
  is distinct from a demonstrated native-generation result.
- Cost measurements are limited to their stated update workload. Timing is
  hardware dependent and excludes prediction/preparation/reference evaluation.
  Existing simple repairs remain sufficient for the tested admission cases.

## Executed validation and denominators

| Validation layer | Recorded result | Interpretation |
| --- | --- | --- |
| Offline V3 | 22,565 checks; zero failed | Reanalysis of saved evidence; no native execution |
| Native command families | 13 families; 322 parity checks passed | Replays of existing conditions; see family records |
| Sensor clean-environment replay | 76 checks per resolution; 8 sequences / 72 updates | Original/single admission, traced/plain, at two existing resolutions |
| All sensor packaging attempts | 12 sequences / 108 updates | Includes the initial 4 completed sequences with a verifier-only failure |
| Saved sensor and pixel audit | 345 checks passed | Offline reanalysis; not additional native sequences |
| Figure extraction | 93 checks passed | Saved-data plot generation |
| Independent Figure 1 review | 46 checks passed | Read-only coordinate, complete-output, prefix and feasibility checks |
| Repair workload | 55 method-case groups x (11 timing + 1 queue + 1 memory) = 715 runs | Warmups separate; not 715 independent scenes |

The sensor first-attempt failure compared Python tuples with serialized JSON
lists; it is retained together with the verifier correction and subsequent
successful replays. A pre-native headless import failure is separately recorded.
Neither is relabeled as a scientific method failure. No failed or unresolved
scientific cases were removed to obtain a passing result.

There are **zero new scientific conditions** in these portability replays. This
does not mean zero native executions: their counts are stated above. The audit
does not combine all command families into an unmeasured total native-update
count. No GPU, physical action, robot completion experiment, or new RFM result
was introduced.

See [release_audit.json](release_audit.json) for machine-readable scope;
[native verification](../reproduce/verification.json),
[output comparisons](../reproduce/output_verification.json),
[sensor portability validation](../reproduce/sensor/PORTABILITY_VALIDATION.md),
[offline transformation verification](../artifact/PUBLIC_COPY_VERIFICATION.json),
and [label correction](../artifact/LABEL_CORRECTION.md) for the underlying records.
