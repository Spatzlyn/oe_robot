#!/usr/bin/env bash
# Linux x86_64; build in a new prefix only. Never changes an existing environment.
set -euo pipefail
OE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OE_PREFIX="${1:-$OE_ROOT/.venv-native}"
OE_CONDA="${CONDA_EXE:-$(command -v conda || true)}"
[[ -n "$OE_CONDA" ]] || { echo 'Install conda or set CONDA_EXE.' >&2; exit 2; }
[[ ! -e "$OE_PREFIX" ]] || { echo 'Refusing to overwrite an existing environment.' >&2; exit 2; }
command -v cmake >/dev/null
command -v g++ >/dev/null
"$OE_CONDA" create -y --prefix "$OE_PREFIX" --file "$OE_ROOT/environment/native-conda-explicit.txt"
OE_PYTHON="$OE_PREFIX/bin/python"
"$OE_PYTHON" -m pip install 'setuptools==59.6.0' 'wheel==0.37.1' 'numpy==1.19.5' 'Cython==0.29.36' 'scikit-build==0.13.1'
"$OE_PYTHON" -m pip install --no-build-isolation -r "$OE_ROOT/environment/native-requirements.txt" -c "$OE_ROOT/environment/native-resolved-lock.txt"
OE_BUILD="$(mktemp -d -t oe-native-build-XXXXXXXX)"
# Keep a failed build for inspection. Successful builds remove only this temporary directory.
cp -a "$OE_ROOT/vendor/rss_occlusion/ThirdParty/octomap-python" "$OE_BUILD/octomap-python"
cp -a "$OE_ROOT/vendor/rss_occlusion/ThirdParty/opendrive2lanelet" "$OE_BUILD/opendrive2lanelet"
export CMAKE_BUILD_PARALLEL_LEVEL=2
export CMAKE_ARGS="-DBUILD_OCTOVIS_SUBPROJECT=OFF"
"$OE_PYTHON" -m pip install --no-deps --no-build-isolation "$OE_BUILD/octomap-python"
"$OE_PYTHON" -m pip install --no-deps --no-build-isolation "$OE_BUILD/opendrive2lanelet"
"$OE_PYTHON" -m pip check
NATIVE_PYTHON="$OE_PYTHON" bash "$OE_ROOT/environment/run_native.sh" "$OE_ROOT/environment/check_native.py"
rm -rf -- "$OE_BUILD"
printf 'Native environment created at %s\n' "$OE_PREFIX"
