import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SERVER_DIR = HERE.parent
sys.path.insert(0, str(SERVER_DIR))

ONSSET_REPO = Path(os.environ.get("ONSSET_UGANDA_REPO", r"C:\Users\corra\Desktop\onsset"))
UGANDA = ONSSET_REPO / "test" / "inputTestUganda"
UGANDA_FILES = {"input_csv": UGANDA / "OnSSET_InputFile_Calibrated_v1.csv", "pv_csv": UGANDA / "ug-2-pv.csv",
                "wind_csv": UGANDA / "ug-2-wind.csv", "mv_lines": UGANDA / "UGA" / "UGA" / "UGA_mv_lines.shp"}
DJIBOUTI_CSV = ONSSET_REPO / "test" / "test_data" / "dj-test.csv"
HAVE_UGANDA = all(p.exists() for p in UGANDA_FILES.values())


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: runs the real OnSSET model (minutes)")


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An isolated workspace and allowed root for the server modules."""
    ws = tmp_path / "ws"
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("ONSSET_WORKSPACE", str(ws))
    monkeypatch.setenv("ONSSET_ALLOWED_ROOTS", str(data))
    return ws, data
