"""Tests for the powerio conversion server and its registry/runner wiring.

The whole module skips when powerio is not installed (it is an opt-in extra).
The FastMCP-decorated tools stay ordinary callables, so we exercise them
in-process without a transport. The launch test lives here rather than in
test_runner.py so it skips with the rest of the module.

tests/data/case9.m is vendored verbatim from
https://github.com/MATPOWER/matpower/tree/master/data (BSD-3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("powerio")

import powerio  # noqa: E402

from powermcp.registry import TOOLS  # noqa: E402

_SERVER_DIR = str(TOOLS["powerio"].resolve_server_dir())
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

import powerio_mcp  # noqa: E402

CASE9 = Path(__file__).resolve().parent / "data" / "case9.m"


def test_parse_case_json_round_trips():
    r = powerio_mcp.parse_case(path=str(CASE9))
    assert r["summary"]["n_buses"] == 9
    assert powerio.from_json(r["json"]).n_buses == 9


def test_normalize_case_returns_dense_one_based_ids():
    r = powerio_mcp.normalize_case(path=str(CASE9))
    case = powerio.from_json(r["json"])
    assert [b["id"] for b in case.buses] == list(range(1, 10))


def test_case_to_json_accepted_downstream():
    r = powerio_mcp.case_to_json(path=str(CASE9))
    assert powerio.from_json(r["json"]).n_buses == 9


def test_compute_matrix_bprime():
    m = powerio_mcp.compute_matrix("bprime", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [9, 9]
    assert m["nnz"] > 0
    assert isinstance(m["nnz"], int)
    # plain Python scalars, not numpy types
    assert type(m["data"][0]) is float
    assert type(m["row"][0]) is int
    assert type(m["col"][0]) is int


def test_compute_matrix_accepts_json_transport():
    transport = powerio_mcp.parse_case(path=str(CASE9))["json"]
    from_json = powerio_mcp.compute_matrix("bprime", json=transport)
    from_path = powerio_mcp.compute_matrix("bprime", path=str(CASE9))
    assert from_json["shape"] == from_path["shape"]
    assert from_json["nnz"] == from_path["nnz"]


def test_compute_matrix_unknown_kind():
    with pytest.raises(ValueError):
        powerio_mcp.compute_matrix("nope", path=str(CASE9))


def test_dense_view_counts():
    d = powerio_mcp.dense_view(path=str(CASE9))
    assert d["n"] == 9
    assert d["m"] == 9
    assert d["base_mva"] == 100.0
    assert type(d["bus_ids"][0]) is int
    assert type(d["branch"]["r"][0]) is float
    assert type(d["is_radial"]) is bool


def test_convert_case_powermodels():
    r = powerio_mcp.convert_case(to="powermodels-json", path=str(CASE9))
    assert isinstance(r["warnings"], list)
    assert len(json.loads(r["text"])["bus"]) == 9


def test_case_summary_fields():
    s = powerio_mcp.case_summary(path=str(CASE9))
    assert s["n_buses"] == 9
    assert s["base_mva"] == 100.0
    assert s["source_format"] == "Matpower"
    assert s["n_connected_components"] == 1
    for key in (
        "name", "n_branches", "n_gens", "n_loads", "n_shunts",
        "is_radial", "connectivity_report",
    ):
        assert key in s


def test_exactly_one_input_enforced():
    with pytest.raises(ValueError):
        powerio_mcp.case_summary()
    with pytest.raises(ValueError):
        powerio_mcp.case_summary(path="x", content="y")
    with pytest.raises(ValueError):
        powerio_mcp.compute_matrix("bprime")
    with pytest.raises(ValueError):
        powerio_mcp.compute_matrix("bprime", path=str(CASE9), json="{}")
    with pytest.raises(ValueError):
        powerio_mcp.dense_view(path="x", content="y")


def test_inline_content_requires_from():
    with pytest.raises(ValueError):
        powerio_mcp.convert_case(to="psse", content=CASE9.read_text())


def test_registry_entry():
    t = TOOLS["powerio"]
    assert t.kind == "open-source"
    assert t.extra == "powerio"
    assert t.run_kind == "script"
    assert t.windows_only is False
    assert t.probe == "powerio"
    assert t.resolve_entry_script().is_file()


@pytest.fixture()
def record_mcp_run(monkeypatch):
    calls = []

    def fake_run(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("mcp.server.fastmcp.FastMCP.run", fake_run, raising=True)
    return calls


def test_launch_powerio_runs_once(record_mcp_run):
    from powermcp import runner

    runner.launch("powerio")
    assert len(record_mcp_run) == 1
    _, kwargs = record_mcp_run[0]
    assert kwargs.get("transport") == "stdio"
