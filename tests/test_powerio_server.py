"""Tests for the powerio conversion server, the PyPSA bridge, and the
registry/runner wiring.

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

_PYPSA_DIR = str(TOOLS["pypsa"].resolve_server_dir())
if _PYPSA_DIR not in sys.path:
    sys.path.insert(0, _PYPSA_DIR)

import pypsa  # noqa: E402  (core dependency, like the server itself)
import pypsa_mcp  # noqa: E402

CASE9 = Path(__file__).resolve().parent / "data" / "case9.m"

# 3-bus case with rating 0 branches, for the overwrite_zero_s_nom tests.
ZERO_RATE_CASE = """function mpc = zero_rate
mpc.version = '2';
mpc.baseMVA = 100.0;
mpc.bus = [
\t1 3 0 0 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
\t2 1 50 10 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
\t3 1 30 5 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
];
mpc.gen = [
\t1 80 0 50 -50 1.0 100 1 200 0 0 0 0 0 0 0 0 0 0 0 0;
];
mpc.branch = [
\t1 2 0.01 0.05 0.0 0 0 0 0 0 1 -360 360;
\t2 3 0.01 0.05 0.0 0 0 0 0 0 1 -360 360;
];
"""


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


def test_compute_matrix_lacpf():
    m = powerio_mcp.compute_matrix("lacpf", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [18, 18]
    assert m["nnz"] > 0
    assert type(m["data"][0]) is float
    assert type(m["row"][0]) is int


def test_save_case_writes_file(tmp_path):
    out = tmp_path / "case9.json"
    r = powerio_mcp.save_case(to="powermodels-json", out_path=str(out), path=str(CASE9))
    assert r["path"] == str(out)
    assert r["bytes_written"] == out.stat().st_size
    assert isinstance(r["warnings"], list)
    assert len(json.loads(out.read_text())["bus"]) == 9


def test_save_case_refuses_overwrite(tmp_path):
    out = tmp_path / "case9.m"
    out.write_text("existing")
    with pytest.raises(ValueError, match="overwrite"):
        powerio_mcp.save_case(to="matpower", out_path=str(out), path=str(CASE9))
    r = powerio_mcp.save_case(
        to="matpower", out_path=str(out), path=str(CASE9), overwrite=True
    )
    assert r["bytes_written"] == out.stat().st_size


def test_save_case_accepts_json_transport(tmp_path):
    transport = powerio_mcp.parse_case(path=str(CASE9))["json"]
    out = tmp_path / "case9.m"
    powerio_mcp.save_case(to="matpower", out_path=str(out), json=transport)
    assert powerio.parse_file(out).n_buses == 9


def test_save_case_exactly_one_input(tmp_path):
    out = tmp_path / "x.m"
    with pytest.raises(ValueError):
        powerio_mcp.save_case(to="matpower", out_path=str(out))
    with pytest.raises(ValueError):
        powerio_mcp.save_case(to="matpower", out_path=str(out), path="a", json="{}")


def test_pypsa_import_case_from_any(tmp_path):
    out = tmp_path / "case9.nc"
    r = pypsa_mcp.import_case_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["network_file"] == str(out)
    assert r["info"]["buses"] == 9
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pypsa_import_case_from_json(tmp_path):
    transport = powerio_mcp.parse_case(path=str(CASE9))["json"]
    out = tmp_path / "case9.nc"
    r = pypsa_mcp.import_case_from_json(transport, str(out))
    assert r["status"] == "success", r
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pypsa_import_reports_dropped_gencost(tmp_path):
    r = pypsa_mcp.import_case_from_any(str(CASE9), str(tmp_path / "c.nc"))
    assert any("cost" in w for w in r["warnings"]), r["warnings"]


def test_pypsa_import_overwrite_zero_s_nom(tmp_path):
    src = tmp_path / "zero.m"
    src.write_text(ZERO_RATE_CASE)

    bare = pypsa_mcp.import_case_from_any(str(src), str(tmp_path / "bare.nc"))
    assert any("rating 0" in w for w in bare["warnings"]), bare["warnings"]

    out = tmp_path / "set.nc"
    r = pypsa_mcp.import_case_from_any(str(src), str(out), overwrite_zero_s_nom=100.0)
    assert not any("rating 0" in w for w in r["warnings"]), r["warnings"]
    assert (pypsa.Network(str(out)).lines.s_nom == 100.0).all()


def test_pypsa_import_missing_file(tmp_path):
    r = pypsa_mcp.import_case_from_any("/nope/missing.m", str(tmp_path / "x.nc"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


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


def test_inline_convert_stages_no_temp_files(monkeypatch):
    # Inline conversion goes through powerio.convert_str entirely in memory;
    # touching tempfile would be a regression to the old staging path.
    import tempfile

    def boom(*args, **kwargs):
        raise AssertionError("inline conversion must not create temp files")

    monkeypatch.setattr(tempfile, "mkstemp", boom)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", boom)
    r = powerio_mcp.convert_case(to="psse", content=CASE9.read_text(), from_="matpower")
    assert r["text"]


# 3-bus case with an out-of-service branch (2-3, status 0) and an out-of-service
# generator (at bus 3, status 0), for the PyPSA/pandapower status tests.
OOS_CASE = """function mpc = oos
mpc.version = '2';
mpc.baseMVA = 100.0;
mpc.bus = [
\t1 3 0 0 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
\t2 1 50 10 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
\t3 1 30 5 0 0 1 1.0 0.0 230.0 1 1.1 0.9;
];
mpc.gen = [
\t1 80 0 50 -50 1.0 100 1 200 0 0 0 0 0 0 0 0 0 0 0 0;
\t3 20 0 50 -50 1.0 100 0 100 0 0 0 0 0 0 0 0 0 0 0 0;
];
mpc.branch = [
\t1 2 0.01 0.05 0.0 250 0 0 0 0 1 -360 360;
\t2 3 0.01 0.05 0.0 250 0 0 0 0 0 -360 360;
];
"""


def test_pypsa_import_drops_out_of_service_branch(tmp_path):
    src = tmp_path / "oos.m"
    src.write_text(OOS_CASE)
    out = tmp_path / "oos.nc"
    r = pypsa_mcp.import_case_from_any(str(src), str(out))
    assert r["status"] == "success", r
    assert pypsa.Network(str(out)).lines.shape[0] == 1  # only the in-service 1-2
    assert any("out-of-service branch" in w for w in r["warnings"]), r["warnings"]


def test_pypsa_import_warns_out_of_service_generator(tmp_path):
    src = tmp_path / "oos.m"
    src.write_text(OOS_CASE)
    r = pypsa_mcp.import_case_from_any(str(src), str(tmp_path / "g.nc"))
    assert r["status"] == "success", r
    assert any("out-of-service generator" in w for w in r["warnings"]), r["warnings"]


def test_pandapower_bridge_honors_branch_status(tmp_path):
    # pandapower's from_ppc models branch status, so the OOS branch should be
    # present but marked out-of-service (not dropped like PyPSA).
    panda_dir = str(TOOLS["pandapower"].resolve_server_dir())
    if panda_dir not in sys.path:
        sys.path.insert(0, panda_dir)
    import panda_mcp  # noqa: E402

    src = tmp_path / "oos.m"
    src.write_text(OOS_CASE)
    res = panda_mcp.load_network_from_any(str(src))
    assert res["status"] == "success", res
    in_service = panda_mcp._current_net.line["in_service"].tolist()
    assert len(in_service) == 2 and in_service.count(False) == 1, in_service


def test_compute_matrix_laplacian():
    m = powerio_mcp.compute_matrix("laplacian", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [9, 9]


def test_compute_matrix_bad_json_raises_valueerror():
    with pytest.raises(ValueError):
        powerio_mcp.compute_matrix("bprime", json="{not valid json")


def test_convert_case_oserror_normalizes_to_valueerror(monkeypatch):
    # An OSError from convert_str (e.g. disk full) must surface as ValueError,
    # not leak as a raw OSError.
    def boom(content, to, from_):
        raise OSError("disk full")

    monkeypatch.setattr(powerio, "convert_str", boom)
    with pytest.raises(ValueError):
        powerio_mcp.convert_case(to="psse", content="x", from_="matpower")


def test_unreadable_file_maps_cleanly(tmp_path):
    # PermissionError must surface as the documented ValueError shape, like
    # FileNotFoundError, not leak raw through the tool. (Ported from the
    # canonical server's suite at powerio 0.1.1.)
    import os

    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("permission bits are not enforceable here")
    locked = tmp_path / "locked.m"
    locked.write_text("function mpc = x\n")
    locked.chmod(0o000)
    try:
        with pytest.raises(ValueError, match="cannot read file"):
            powerio_mcp.convert_case(to="psse", path=str(locked))
        with pytest.raises(ValueError, match="cannot read file"):
            powerio_mcp.case_summary(path=str(locked))
    finally:
        locked.chmod(0o644)


def test_wrong_schema_json_maps_cleanly():
    # Wrong-schema (but well-formed) JSON keeps the one error shape too; the
    # malformed-JSON case is covered above.
    for bad in ("{}", "[]", "null", '{"buses": "nope"}'):
        with pytest.raises(ValueError, match="parse failed"):
            powerio_mcp.compute_matrix("bprime", json=bad)


# ---------------------------------------------------------------------------
# ANDES bridge tests
# ---------------------------------------------------------------------------

def _load_andes_mcp():
    """Import andes_mcp from the registry-resolved server dir, skipping if
    andes or powerio are not installed."""
    pytest.importorskip("andes")
    andes_dir = str(TOOLS["andes"].resolve_server_dir())
    if andes_dir not in sys.path:
        sys.path.insert(0, andes_dir)
    import andes_mcp  # noqa: E402
    return andes_mcp


def test_andes_load_network_from_any(tmp_path):
    andes_mcp = _load_andes_mcp()
    out = tmp_path / "case9.m"
    r = andes_mcp.load_network_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["case_file"] == str(out)
    assert r["info"]["buses"] == 9


def test_andes_load_network_from_json(tmp_path):
    andes_mcp = _load_andes_mcp()
    transport = powerio_mcp.parse_case(path=str(CASE9))["json"]
    out = tmp_path / "case9_from_json.m"
    r = andes_mcp.load_network_from_json(transport, str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["info"]["buses"] == 9


def test_andes_load_missing_file(tmp_path):
    andes_mcp = _load_andes_mcp()
    r = andes_mcp.load_network_from_any("/nope/missing.m", str(tmp_path / "x.m"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()
