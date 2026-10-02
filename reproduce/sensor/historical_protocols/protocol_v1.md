# C1 sensor realization — bounded development protocol

Frozen before the first new native execution (2026-09-24 UTC).

## Question and evidence level
Can a fixed opaque scene, a moving camera, full generated depth images, and the
unmodified native DepthVisibility + update_visibility + predict_shadow pipeline
produce the short job → registered key → mature=None → long re-entry rejection
mechanism and whole-output loss of an independently hidden stationary witness?
This is a synthetic sensor-model existence test, not a CARLA rollout, a natural
scene frequency estimate, or an observation-equivalence proof.

## Generation and constants
CPU pinhole rendering of every pixel, four yaw-separated cameras, 640×360,
horizontal FOV 110°, optical-axis depth (not Euclidean range), far plane 1000 m.
Opaque fixed vertical panels at y=-5, height 0..4 m; no time-indexed visibility
mask and no pixel assignment based on native ds queries. Camera height 1.7 m,
y=-10 m, x=-4+v*t. Times 0..4 in steps of 0.5 s. v ∈ {0,0.5,1} m/s.
Target lane1 x=ds, y=0, ds20→0; lane2 x=ds-10, ds10→0.
Ego route polyline (-20,-10)→(0,-10)→(0,10), positive traffic direction.
Its crossing of the target shared endpoint grounds the synthetic cross metadata.
Native road-map loader/CARLA is not used: Lane/client/map boundary objects are
explicit synthetic fixtures, while shadow initialization and all subsequent
shadow construction/prediction/update are native.

Panel geometry development grid is fixed below before results:
left panel x=[-1, -0.75], right panel left x ∈ {-0.5,-0.25,0},
right panel right x=5.5. Under camera x=-4, central projection produces a short
occluded component and a long component. Stationary witness has front ds8,
length3 m, width1 m, height1.5 m; zero velocity/acceleration. Witness volume
must be occluded by an independent geometric segment-panel test at every
observation; sufficient interval bounds must establish the continuous body,
not just native waypoint samples. No new hidden births are assumed.
Native v_max15, acceleration[-8,4], ds0.5, stop_length40, range100 unchanged.

## Discovery/confirmation distinction
Nine geometry/motion combinations are development, all retained. No claim of
held-out generalization. Before an intervention replay, record the selected
scene, epoch, native key and exact target rule in a separate freeze JSON.
If the mechanism is found, compare Original, single target admission,
admission-OFF, mature-only-OFF, and current mature guard with identical image
bytes/poses/initialization. The target-free baseline remains a valid negative.
Instrumentation must have whole-output parity with a separate uninstrumented
execution at all epochs. No behavior-changing sensor adapter fixes are allowed
inside a method comparison.

## Recorded outcomes and criteria
Every run records raw full depth arrays, all camera transforms, lane geometry,
native queried visibility, initialized/propagated inputs, key registration,
primitive return, candidate admission/mature decisions, full output at each
epoch, native wrapper reinitialization, status/error, and source hashes.
Whole-position absence is decisive only if no explicit or unresolved implicit
tail can cover the independently feasible witness. Position recovery alone is
not a velocity/history or continuous soundness certificate.
Target absent, target present without witness loss, intervention unapplied,
invalid execution, semantic unresolved, and witnessed omission remain separate.
No effect is attributed to a target intervention unless application is logged.
No completion/collision inference or cost/real-time claim is planned.
Permission evaluation is conditional on a meaningful fixed same-scene query;
an old D05 checker transplant would be labeled a separate fixture, not an
end-to-end sensor-scene driving result.

## Changes
Any model/input/timing change is a new protocol condition. Logger-only changes
preserve old traces and require native I/O parity. Other processes and GPUs are
not used or interrupted.
