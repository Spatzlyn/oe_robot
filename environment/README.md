# Environments

## Offline result verification

Use Python 3.10 or later. The offline validator uses the Python standard library and reads saved JSON/CSV records. It does not require CARLA, OctoMap, NumPy, a simulator, or a GPU.

```bash
python artifact/validate_offline_v3.py --artifact artifact --output /tmp/oe_robot_offline_check
```

## Figure generation

Use a separate modern Python environment (Python 3.10–3.13):

```bash
python -m venv .venv-figures
.venv-figures/bin/python -m pip install -r environment/figure-requirements.txt
```

The Figure 1 README gives the generation command and expected coordinate/membership checks. Regenerating a figure is not a new sensor or checker experiment.

## Native controlled, checker, repair, pruning, and sensor replays

The recorded native environment is **Linux x86_64, CPython 3.7.12**. A fresh-prefix installation and source build were tested for this release; see [installation_verified.json](installation_verified.json). This path does not start a simulator or use a GPU.

Prerequisites: conda, a C/C++ compiler, CMake, and the system shared libraries used by OpenCV/Open3D/pygame (on Ubuntu, commonly `libgl1`, `libglib2.0-0`, `libgomp1`, `libsm6`, and `libxrender1`). System packages are not automatically installed by the script.

```bash
bash environment/setup_native.sh
bash environment/run_native.sh environment/check_native.py
bash environment/run_native.sh reproduce/run.py --help
```

The installer refuses to overwrite an existing prefix. It installs pinned packages, builds the upstream-modified OctoMap binding and opendrive2lanelet from the bundled sources, then performs `pip check` and native import checks. It limits compilation to two jobs and disables the unused Octovis viewer build. Failed temporary builds remain available for inspection.

To use an existing compatible environment:

```bash
NATIVE_PYTHON=/path/to/native/bin/python bash environment/run_native.sh reproduce/run.py --help
```

`run_native.sh` supplies the bundled official CARLA 0.9.11 Python egg and helper modules, the analyzed implementation, headless graphics settings and a CPU-only device setting. It does not start a CARLA process. The downloaded native API is architecture/version specific; do not use the CPython 3.7 egg with a different Python version.

`historical-pip-lock.txt` records the original environment. `native-requirements.txt` identifies direct runtime/build dependencies. `native-resolved-lock.txt` pins the transitive packages from the fresh installation test. Small transitive-version differences from the historical environment are recorded rather than described as bitwise environment identity.

The historical locally compiled OctoMap wheel is deliberately not distributed: it embeds private build paths. The included source build avoids dependence on that server binary. Recompiling may produce a different wheel hash; scientific result parity is evaluated separately.

The four pre-existing implementation compatibility changes are recorded in `compatibility.patch`. They concern headless plotting, Traffic Manager port handling, and sensor readiness metadata. The scientific shadow and checker modules are byte-identical to the pinned upstream revision. These CPU replays do not exercise live sensor callback readiness or Traffic Manager control.
