"""Make the adjacent PowerFactory implementation importable for its tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# This script runs against an installed wheel in a separate CI environment.
collect_ignore = ["test_evemtbench_wheel.py"]
