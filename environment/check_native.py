"""Import checks only: this does not connect to or start a simulator."""
import sys
import json
if sys.version_info[:2] != (3, 7):
    raise SystemExit('Native artifact requires CPython 3.7; recorded version is 3.7.12.')
import numpy
import carla
import octomap
import client
import planning
from risk_analysis.shadow_utils import ShadowUtils
from risk_analysis.state_checker import StateChecker
print(json.dumps({'status': 'imports_passed', 'python': sys.version.split()[0], 'numpy': numpy.__version__, 'simulator_started': False, 'device': 'CPU'}))
