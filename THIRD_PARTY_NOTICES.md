# Third-party code and data

The names below identify the authors of the analyzed implementation and its dependencies, not the authors of this submission. Copyright and license notices are intentionally retained.

## Analyzed implementation

`vendor/rss_occlusion/` contains the runtime modules and necessary build source from **Safe Occlusion-Aware Autonomous Driving via Game-Theoretic Active Perception**, Zixu Zhang and Jaime F. Fisac, RSS 2021.

- Upstream: <https://github.com/SafeRoboticsLab/Safe_Occlusion_Aware_Planning>
- Revision: `2b6b06637850b406cfbeab926a3dedc01edad91e`.
- License: [BSD 3-Clause](vendor/rss_occlusion/LICENSE); retained without alteration.
- File-level upstream/public hashes: [docs/upstream_files.json](docs/upstream_files.json).
- Pre-existing compatibility changes: [environment/compatibility.patch](environment/compatibility.patch). The shadow propagation and safety checker source files are unchanged. Research instrumentation and interventions live in `reproduce/`, not in these scientific modules.

Upstream subcomponents retain their individual notices:

- `ThirdParty/opendrive2lanelet/`: GNU GPL version 3 text is retained in its `LICENSE.txt`; consult that file and the package's per-file notices.
- `ThirdParty/octomap-python/`: modified Python binding distributed by the analyzed repository; source package declares BSD. OctoMap, dynamicEDT3D and optional Octovis components retain their own license files. The native installer disables the optional Octovis viewer build.
- [OctoMap license](vendor/rss_occlusion/ThirdParty/octomap-python/src/octomap/octomap/LICENSE.txt).
- [dynamicEDT3D license](vendor/rss_occlusion/ThirdParty/octomap-python/src/octomap/dynamicEDT3D/LICENSE.txt).

## CARLA Python API

`environment/third_party/carla-0.9.11-py3.7-linux-x86_64.egg` and `environment/third_party/carla/agents/` are from the official CARLA 0.9.11 Linux distribution. They are required by upstream Python imports; this artifact does not start a CARLA server or redistribute simulator assets.

- Upstream: <https://github.com/carla-simulator/carla/tree/0.9.11>.
- [MIT license](environment/third_party/CARLA_LICENSE), retained.
- The distributed CPython 3.7 egg is unmodified. Its digest is included in the public file manifest.

## Other dependencies and inputs

NumPy, SciPy, Shapely, Matplotlib and other packages are installed separately under their own licenses. See `environment/native-requirements.txt` and `environment/historical-pip-lock.txt`.

The fixed checker snapshot and reconstructed occupancy map are derived experimental inputs, not a CARLA simulator distribution. See `fixtures/` for reconstruction scope and hashes. The map is supplied compressed and must pass its byte digest check before use; an empty-map fallback is not accepted.

This notice does not relicense third-party material or replace any retained per-file or package license.
