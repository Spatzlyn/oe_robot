# Synthetic depth and native shadow update

This package reproduces the paper's sensor-generated existence example. A fixed
ideal scene generates full depth images; the pinned implementation's
`DepthVisibility`, native empty-list initialization, `predict_shadow`, and
`update_visibility` then produce the returned shadows. The lane/network/client
interfaces are explicitly synthetic. No CARLA server, GPU, learned policy,
task-completion experiment, or same-scene action checker is invoked.

## Quick audit of saved records

From the repository root, with NumPy installed:

```bash
python reproduce/sensor/verify_saved.py --output results/sensor_saved_check
# Optional independent slab-intersection check against every saved pixel:
python reproduce/sensor/verify_saved.py --pixel-check --output results/sensor_pixel_check
```

The first command recomputes finite-tree position membership, an independent
analytic body-occlusion certificate, traced/plain parity, identical-prefix
checks, and public file hashes. It does **not** execute the native update or
render new images. The optional command checks that adding the feasible body
changes zero stored depth pixels; this is not a real-object detection claim.

## Fresh native reproduction

Install the native environment described at repository-root
`environment/README.md`.
Use the repository's Python 3.7 native wrapper:

```bash
bash environment/run_native.sh reproduce/sensor/run_sensor.py \
  --resolution 640 --output results/sensor640
bash environment/run_native.sh reproduce/sensor/run_sensor.py \
  --resolution 1920 --output results/sensor1920
```

Both commands render all nine epochs and four cameras on CPU, then run
Original and the frozen single-admission intervention, each traced and plain.
The output directory must not already exist. `--upstream PATH` overrides the
default `vendor/rss_occlusion` checkout. The default is the upstream source
revision `2b6b06637850b406cfbeab926a3dedc01edad91e` plus documented import
compatibility changes; hashes of all three relevant native files must match
the historical record.

To reproduce all existing controls in the selected 640-pixel condition:

```bash
bash environment/run_native.sh reproduce/sensor/run_sensor.py \
  --resolution 640 \
  --methods original,single_admission,admission_off,mature_only_off,mature_guard \
  --output results/sensor640_controls
```

For 1920 pixels the historically tested methods are `original`,
`single_admission`, and `admission_off`; the wrapper rejects other methods to
avoid silently expanding the experiment. Historical nine-condition development
results are distributed in full, but the default commands do not sweep them.

## Expected result

| Resolution | Original: feasible position absent at | Single admission | Intervention time |
|---|---|---|---|
| 640×360 | 2.0, 3.5, 4.0 s | Restored at 2.0 s; absent at 3.5 and 4.0 s | 2.0 s |
| 1920×1080 | 3.5 s | Present at all nine saved epochs | 3.5 s |

At 1920 pixels, Original regenerates the position at 4.0 s without an
intervention. This does not undo the omission at 3.5 s. The earlier short job
retains a mature output at the 1920 target: `mature=None` is **not** required.
The searched-key/visited records reset per update; the mechanism is within
one update, not a stale cache spanning observations.

The designated witness has front/reference point `(lane 1, ds=8 m)` and
stationary body `x∈[8,11], y∈[-0.5,0.5], z∈[0,1.5] m`, `v=a=0`.
Its feasibility certificate uses ray/screen geometry independently of native
shadow membership. Every point of the body is behind the right opaque panel
throughout the selected camera path. The body is a **possible** hidden object,
not an object inserted into the original rendered scene.

At 640 pixels, `admission_off` and the restricted `mature_guard` retain this
witness at all saved epochs. `mature_only_off` leaves the target omission in
place. These whole-sequence controls are not identical-prefix interventions.
They establish neither coverage of every continuous state nor universal
soundness of the corresponding methods. Changing image resolution changes
the observation operator; it is not a new independent scene or proof of
global observation equivalence.

## What is generated

- `start_manifest.json`: code/protocol/native hashes, command and CPU scope.
- `v0.5_g-0.5/depth.npz`, `sensor_poses.json`, `scene.json`: generated inputs.
- Each method's JSON and `_plain.json`: complete outputs, visibility queries,
  processing/admission events, exact intervention application and errors.
- `paired_intervention.json`: same-prefix and single-target comparison.
- `whole_output_semantic_audit.json`: typed membership and independent
  feasibility at every epoch; unresolved tails remain explicit.
- `verification.json`: source/input/output parity against saved expectations.

The fresh commands each run 2 traced + 2 plain sequences = 36 native updates.
Historical records contain 17 traced + 17 plain sequences = 306 updates:
9 development Original conditions, 5 selected 640 methods, 2 selected 1920
controls, and 1 selected 1920 single-admission replay. These overlap; they
must not be counted as 17 independent scenes. One failed pre-native
instrumentation attempt is retained separately and has no method outcome.

## Provenance and changes

`expected/` contains sanitized historical records including negative results,
the failed instrumentation attempt, and complete method outputs.
`historical_protocols/` preserves original protocol stages; source hashes
explicitly marked `historical_*` refer to pre-publication files.
`protocols/` fixes the portable replay's selected geometry, resolution and
single-admission target. `public_manifest.json` hashes the actual distributed
input bytes. Public copies remove private filesystem locations and process
identifiers; source snapshots under `expected/` are archival records, not
executable entry points. Use `run_sensor.py`.

The portable runner changes import/output paths and adds verification. It
reuses the renderer, manager boundary, native execution, instrumentation,
intervention predicate and witness settings. The fresh replay must match
stored full depth arrays, poses, native outputs, events and visibility queries
before being described as a successful reproduction.

`semantics.py` uses the existing offline v3 typed finite-tree decoder. Its
terminal `InBound` handling prevents a generic leaf flag from being mistaken
for an unresolved infinite tail. Position presence does not certify velocity
or history; unknown nodes/tails are not silently treated as absent. Archived
labels remain available alongside newly audited classifications.

The paper's 18→4 permission result belongs to a **separate checker fixture**.
No collision, task success, natural-scene occurrence rate, continuous
soundness, or direct RFM benefit is measured by these sensor runs.
