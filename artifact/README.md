# Offline evidence audit

This directory provides a portable, standard-library-only audit of the archived
experiments. It recomputes designated-witness checks and accounting from saved
inputs, complete outputs, events, and fixed checker queries. **It does not rerun
the native planner, render depth images, drive a simulator, or reproduce a
closed-loop robot episode.** Use the repository's native reproduction commands
for those separate tasks.

## Quick start

From the repository root, with Python 3.8 or later:

```bash
python artifact/validate_offline_v3.py --artifact artifact --output /tmp/oe_robot_offline_check
```

The output directory must not already exist. Choose another directory for each
run; the validator deliberately refuses to overwrite an earlier audit. No
packages, network access, GPU, simulator, or pickle loading are required. The
public release was checked with the Python version recorded in
`validation_public/validation_results.json`.

Expected terminal result:

```json
{"checks": 22565, "failed": 0, "outputs": 1410, "queries": 180}
```

The terminal JSON also reports the selected output path. A failed consistency
check returns exit code 1; an invalid input or existing output directory also
fails. The number of checks is not an experiment, scene, or episode denominator.

## What is recomputed

| Evidence group | Included check | Scope |
| --- | --- | --- |
| Original finite model fixture | Finite feasible-state reference, designated stationary witness, whole-output position membership, local intervention and preservation controls | Finite hypotheses under the recorded model; not continuous soundness |
| Synthetic-depth fixture | Recorded depth/pose parity, independent fixed-panel body-occlusion certificate, whole-output intervals and targeted admission record | Ideal synthetic geometry and the saved observation schedule |
| Legacy fixed checker fixture | 18 identical candidate tuples for each near/far arm; native verdict accounting | Separate model-level transplanted fixture; not the sensor scene's end-to-end result |
| Constructed boundary cases | Missing/retained witness positions, alternate-owner control, unresolved semantics | Constructed input cases, distinct from native reachability |
| Native-generation search | Full recorded condition and witness-time denominators, local cause-attribution scope | Search evidence; a negative result does not establish impossibility |
| Diagnostic shortcuts | Empty-output, representative-existence, final-only, rejection and patch-consensus limits | Selected counterexamples; not detection accuracy |
| Source and byte provenance | Every archive member's public SHA256, executed source lineage, public V2/V3 record parity | Integrity and attribution; hashes alone do not establish scientific validity |

The C1 `searched`/`visited` processing records are initialized on each update.
The C1 mechanism concerns a processing record within **one update**, not a cache
stale across multiple observation times. `mature=None` is not a necessary
condition. Later regeneration does not undo an earlier omission.

## Expected scientific accounting

- The old model fixture has 293 finite reference hypotheses at the final epoch.
  These are not 293 independent episodes.
- The legacy checker near fixture permits 18/18 candidates in the original arm
  and 4/18 in each recorded comparison arm. There are 14 permission differences,
  not 14 collisions. The far fixture permits 18/18 in each arm. Its input changes
  are not a one-factor distance ablation.
- The 1920 x 1080 synthetic-depth original omits the designated position at
  3.5 s; the same-prefix single admission retains it. The 640 x 360 fixture and
  the legacy checker fixture are separate evidence groups.
- The sensor collection contains 17 traced and 17 plain sequences, 306 total
  updates, and one separately recorded pre-native instrumentation failure.
- The native D1 search contains 256 primary conditions and 1,280 updates.
  There are 35 conditions with missing designated positions, comprising 104
  witness-times. Exactly **2 witness-times have the recorded local cause
  attribution and 102 remain unresolved**. See [LABEL_CORRECTION.md](LABEL_CORRECTION.md).
- The constructed mature-output counterexample is not a demonstrated
  naturally generated D1 failure: the recorded native search confirmed zero
  harmful mature-output D1 conditions.

## Files and data access

- `evidence.zip`: 651 archive members, about 7.1 MB compressed and 235.2 MB
  uncompressed; relative paths preserve the evidence grouping.
- `manifest.json`: public archive/member hashes and external-input limitations.
- `expected.json`: retrospective regression expectations, not new predictions.
- `protocol.json`: original retrospective scope and tolerances.
- `validation_v2/`: historical normalized baseline, with public path/hash
  transformations only. Its cause labels are intentionally superseded.
- `validation_public/`: output of the shipped V3 validator on the public bundle.
- `ANONYMIZATION.json`: explicit transformation record and public hashes.
- `PUBLIC_COPY_VERIFICATION.json`: independent structure/scalar, source-AST and
  nested numeric-array checks of the anonymous transformation.
- `bundle_manifest.json`: SHA256 and size of every public file in this directory
  other than the manifest itself.
- `SCHEMA.md` and `TRUST_AND_LIMITS.md`: interpretation and limits.

Inspect or extract the archive without executing historical source snapshots:

```bash
python -m zipfile -l artifact/evidence.zip
python -m zipfile -e artifact/evidence.zip /tmp/oe_robot_evidence
```

The validator reads the ZIP directly. An extraction is optional and requires
about 235 MB of additional disk space. The archive also preserves negative
results, exploratory records, unresolved cases, historical source snapshots,
and failed instrumentation records. Some historical notes are in Korean;
the reviewer-facing instructions and scope documents here are in English.

Four legacy pickle contexts are documented but not bundled in this offline
package. The validator checks their collection-time hash accounting and never
claims to replay them. The archived environment locks record the historical
environment; they are not a portable installation command or a declaration that
unbundled wheels, CARLA, or map assets are included.

## Anonymous distribution

Personal absolute paths and private Drive links were removed from public
copies. Archived sensor harness path discovery uses `OE_ROBOT_SOURCE_ROOT`
(or the current directory). Source-hash references and archive hashes were
recomputed accordingly. No measurements, geometry, model parameters, forests,
action tuples, witness states, or verdicts were changed. All 13 NPZ payloads are
byte-identical to their historical copies. The public archive intentionally has
a different hash from the private collection; do not substitute one for the other.

The offline validator's scientific checks are unchanged. Its public version adds
an explicit nonzero exit status on failed checks and describes the transformed
provenance. Third-party source remains subject to the upstream license and the
repository's third-party notices.
