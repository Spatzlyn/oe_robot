#!/usr/bin/env bash
set -euo pipefail
OE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OE_PYTHON="${NATIVE_PYTHON:-$OE_ROOT/.venv-native/bin/python}"
[[ -x "$OE_PYTHON" ]] || { echo 'Run environment/setup_native.sh, or set NATIVE_PYTHON to a compatible CPython 3.7 interpreter.' >&2; exit 2; }
export PYTHONPATH="$OE_ROOT/environment/third_party/carla-0.9.11-py3.7-linux-x86_64.egg:$OE_ROOT/environment/third_party/carla:$OE_ROOT/vendor/rss_occlusion${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$(dirname -- "$(dirname -- "$OE_PYTHON")")/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg PYGLET_HEADLESS=true SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
exec "$OE_PYTHON" "$@"
