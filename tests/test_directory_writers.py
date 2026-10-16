"""Consumer checks for servers that install complete directory outputs."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _load_surge_server(monkeypatch):
    fake_surge = types.ModuleType("surge")
    fake_surge.Network = type("Network", (), {})
    monkeypatch.setitem(sys.modules, "surge", fake_surge)
    path = Path(__file__).resolve().parents[1] / "surge" / "surge_mcp.py"
    spec = importlib.util.spec_from_file_location("surge_mcp_directory_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_surge_table_export_is_staged_and_preserves_unrelated_files(
    tmp_path, monkeypatch
):
    server = _load_surge_server(monkeypatch)

    class Network:
        def bus_dataframe(self):
            return {"id": [1]}

        def branch_dataframe(self):
            return {"id": [1]}

        def gen_dataframe(self):
            return {"id": [1]}

        def loads_dataframe(self):
            return {"id": [1]}

        def shunts_dataframe(self):
            return {"id": [1]}

    server._current_net = Network()
    output = tmp_path / "tables"
    output.mkdir()
    (output / "keep.txt").write_text("keep")

    result = server.export_tables(str(output))
    assert result["status"] == "success", result
    assert (output / "keep.txt").read_text() == "keep"
    assert {path.name for path in output.glob("*.csv")} == {
        "buses.csv",
        "branches.csv",
        "generators.csv",
        "loads.csv",
        "shunts.csv",
    }
