"""Tests for the powerio conversion server, the PyPSA bridge, and the
registry/runner wiring.

powerio is a core dependency, so it is normally present; the importorskip below
stays as insurance for stripped-down environments.
The FastMCP-decorated tools stay ordinary callables, so we exercise them
in-process without a transport. The launch test lives here rather than in
test_runner.py so it skips with the rest of the module.

tests/data/case9.m is vendored verbatim from
https://github.com/MATPOWER/matpower/tree/master/data (BSD-3).
tests/data/powerworld/ACTIVSg200.pwd is vendored from powerio's test suite
(eigenergy/powerio); ACTIVSg200 is a public Texas A&M synthetic grid.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("powerio", minversion="0.4.0")

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
ACTIVSG200_PWD = (
    Path(__file__).resolve().parent / "data" / "powerworld" / "ACTIVSg200.pwd"
)
MINIMAL_BMOPF = '{"bus":{"a":{"terminal_names":["1"]}}}'

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


def test_parse_json_round_trips():
    r = powerio_mcp.parse(path=str(CASE9))
    assert r["schema"] == "powerio.parse"
    assert r["schema_version"] == "0.1"
    assert r["domain"] == "transmission"
    assert r["model"] == "balanced"
    assert r["json_format"] == "powerio-json"
    assert r["source_format"] == "Matpower"
    assert isinstance(r["warnings"], list)
    assert r["summary"]["elements"]["buses"] == 9
    assert powerio.from_json(r["json"]).n_buses == 9


def test_tool_surface_is_canonical():
    tools = {tool.name: tool for tool in asyncio.run(powerio_mcp.mcp.list_tools())}
    names = set(tools)
    assert names == {
        "convert",
        "save",
        "summary",
        "parse",
        "normalize",
        "matrix",
        "diagnostics",
        "display",
    }
    for name in ("parse", "summary", "normalize", "matrix", "display"):
        props = tools[name].inputSchema["properties"]
        assert "from_format" in props
        assert "format" not in props
    parse_props = tools["parse"].inputSchema["properties"]
    assert "transport" in parse_props
    convert_props = tools["convert"].inputSchema["properties"]
    assert "to_format" in convert_props and "from_format" in convert_props
    assert "package_json" in convert_props
    assert "to" not in convert_props and "format" not in convert_props
    for name in ("summary", "normalize", "matrix"):
        assert "package_json" in tools[name].inputSchema["properties"]
    save_schema = tools["save"].inputSchema
    assert save_schema["required"] == ["out_path"]
    save_props = save_schema["properties"]
    assert "to_format" in save_props and "from_format" in save_props
    assert "package_json" in save_props
    assert "to" not in save_props and "format" not in save_props


def test_normalize_returns_dense_one_based_ids():
    r = powerio_mcp.normalize(path=str(CASE9))
    case = powerio.from_json(r["json"])
    assert [b["id"] for b in case.buses] == list(range(1, 10))


def test_parse_transport_accepted_downstream():
    r = powerio_mcp.parse(path=str(CASE9))
    assert powerio.from_json(r["json"]).n_buses == 9


def test_matrix_bprime():
    m = powerio_mcp.matrix("bprime", path=str(CASE9))
    assert m["schema"] == "powerio.matrix"
    assert m["schema_version"] == "0.1"
    assert m["domain"] == "transmission"
    assert m["model"] == "balanced"
    assert m["json_format"] == "powerio-json"
    assert m["source_format"] == "Matpower"
    assert isinstance(m["warnings"], list)
    assert m["format"] == "coo"
    assert m["shape"] == [9, 9]
    assert m["nnz"] > 0
    assert isinstance(m["nnz"], int)
    # plain Python scalars, not numpy types
    assert type(m["data"][0]) is float
    assert type(m["row"][0]) is int
    assert type(m["col"][0]) is int


def test_matrix_accepts_json_transport():
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
    from_json = powerio_mcp.matrix("bprime", json=transport)
    from_path = powerio_mcp.matrix("bprime", path=str(CASE9))
    assert from_json["shape"] == from_path["shape"]
    assert from_json["nnz"] == from_path["nnz"]


def test_matrix_unknown_kind():
    with pytest.raises(ValueError):
        powerio_mcp.matrix("nope", path=str(CASE9))


def test_convert_powermodels():
    r = powerio_mcp.convert(to_format="powermodels-json", path=str(CASE9))
    assert isinstance(r["warnings"], list)
    assert len(json.loads(r["text"])["bus"]) == 9


def test_summary_fields():
    s = powerio_mcp.summary(path=str(CASE9))
    assert s["schema"] == "powerio.summary"
    assert s["schema_version"] == "0.1"
    assert s["domain"] == "transmission"
    assert s["model"] == "balanced"
    assert s["json_format"] == "powerio-json"
    assert isinstance(s["warnings"], list)
    assert s["elements"]["buses"] == 9
    assert s["base_mva"] == 100.0
    assert s["source_format"] == "Matpower"
    assert s["topology"]["connected_components"] == 1
    assert s["elements"]["branches"] == 9
    assert s["topology"]["connectivity_report"]


def test_exactly_one_input_enforced():
    with pytest.raises(ValueError):
        powerio_mcp.summary()
    with pytest.raises(ValueError):
        powerio_mcp.summary(path="x", content="y")
    with pytest.raises(ValueError):
        powerio_mcp.matrix("bprime")
    with pytest.raises(ValueError):
        powerio_mcp.matrix("bprime", path=str(CASE9), json="{}")


def test_inline_matpower_content_defaults_to_matpower():
    assert powerio_mcp.convert(to_format="psse", content=CASE9.read_text())["text"]


def test_matrix_lacpf():
    m = powerio_mcp.matrix("lacpf", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [18, 18]
    assert m["nnz"] > 0
    assert type(m["data"][0]) is float
    assert type(m["row"][0]) is int


def test_save_writes_file(tmp_path):
    out = tmp_path / "case9.json"
    r = powerio_mcp.save(
        to_format="powermodels-json", out_path=str(out), path=str(CASE9)
    )
    assert r["path"] == str(out)
    assert r["bytes_written"] == out.stat().st_size
    assert isinstance(r["warnings"], list)
    assert len(json.loads(out.read_text())["bus"]) == 9


def test_save_refuses_overwrite(tmp_path):
    out = tmp_path / "case9.m"
    out.write_text("existing")
    with pytest.raises(ValueError, match="overwrite"):
        powerio_mcp.save(out_path=str(out), path=str(CASE9))
    r = powerio_mcp.save(
        out_path=str(out), path=str(CASE9), overwrite=True
    )
    assert r["bytes_written"] == out.stat().st_size


def test_save_accepts_json_transport(tmp_path):
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
    out = tmp_path / "case9.m"
    powerio_mcp.save(out_path=str(out), json=transport)
    assert powerio.parse_file(out).n_buses == 9


def test_package_transport_flows_through_core_tools(tmp_path):
    parsed = powerio_mcp.parse(path=str(CASE9), transport="package")
    assert parsed["schema"] == "powerio.parse"
    assert parsed["transport"] == "package"
    assert parsed["json_format"] == "package"
    assert parsed["domain"] == "transmission"
    assert parsed["model"] == "balanced"
    assert "package_json" in parsed

    package = json.loads(parsed["package_json"])
    assert package["model_kind"] == "balanced"
    assert package["model"]["kind"] == "balanced"

    package_json = parsed["package_json"]
    assert powerio_mcp.summary(package_json=package_json)["elements"]["buses"] == 9

    matrix = powerio_mcp.matrix("bprime", package_json=package_json)
    assert matrix["kind"] == "bprime"
    assert matrix["shape"] == [9, 9]

    out = tmp_path / "case9.m"
    powerio_mcp.save(out_path=str(out), package_json=package_json)
    assert powerio.parse_file(out).n_buses == 9

    diag = powerio_mcp.diagnostics(package_json)
    assert diag["schema"] == "powerio.diagnostics"
    assert diag["model_kind"] == "balanced"
    assert diag["summary"]["status"] in {"ok", "info", "warning", "error", "fatal"}
    assert isinstance(diag["summary"]["text"], str)
    assert isinstance(diag["diagnostics"], list)


def test_save_exactly_one_input(tmp_path):
    out = tmp_path / "x.m"
    with pytest.raises(ValueError):
        powerio_mcp.save(out_path=str(out))
    with pytest.raises(ValueError):
        powerio_mcp.save(out_path=str(out), path="a", json="{}")


def test_pypsa_import_case_from_any(tmp_path):
    out = tmp_path / "case9.nc"
    r = pypsa_mcp.import_case_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["network_file"] == str(out)
    assert r["info"]["buses"] == 9
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pypsa_import_case_from_json(tmp_path):
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
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
    assert t.extra is None  # promoted to a core dependency (issue #30)
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
    r = powerio_mcp.convert(
        to_format="psse", content=CASE9.read_text(), from_format="matpower"
    )
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


def test_matrix_laplacian():
    m = powerio_mcp.matrix("laplacian", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [9, 9]


def test_matrix_bad_json_raises_valueerror():
    with pytest.raises(ValueError):
        powerio_mcp.matrix("bprime", json="{not valid json")


def test_convert_oserror_normalizes_to_valueerror(monkeypatch):
    # An OSError from convert_str (e.g. disk full) must surface as ValueError,
    # not leak as a raw OSError.
    def boom(content, to, from_):
        raise OSError("disk full")

    monkeypatch.setattr(powerio, "convert_str", boom)
    with pytest.raises(ValueError):
        powerio_mcp.convert(to_format="psse", content="x", from_format="matpower")


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
        with pytest.raises(ValueError, match="cannot read input"):
            powerio_mcp.convert(to_format="psse", path=str(locked))
        with pytest.raises(ValueError, match="cannot read input"):
            powerio_mcp.summary(path=str(locked))
    finally:
        locked.chmod(0o644)


def test_wrong_schema_json_maps_cleanly():
    # Wrong-schema (but well-formed) JSON keeps the one error shape too; the
    # malformed-JSON case is covered above.
    for bad in ("{}", "[]", "null", '{"buses": "nope"}'):
        with pytest.raises(ValueError, match="parse failed"):
            powerio_mcp.matrix("bprime", json=bad, json_format="powerio-json")


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
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
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


# ---------------------------------------------------------------------------
# pandapower-json plus folder and Parquet formats routed through generic verbs.
# ---------------------------------------------------------------------------

def test_convert_to_pandapower_json():
    r = powerio_mcp.convert(to_format="pandapower-json", path=str(CASE9))
    assert r["text"]
    assert json.loads(r["text"])  # well-formed JSON


def test_pandapower_json_round_trips_through_transport():
    # pandapower-json is a plain text format, so it flows through the existing
    # save/parse tools with no dedicated tool.
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
    out = powerio_mcp.parse(
        content=powerio_mcp.convert(to_format="pandapower-json", path=str(CASE9))[
            "text"
        ],
        from_format="pandapower-json",
    )
    assert json.loads(out["json"])
    assert json.loads(transport)


def test_pypsa_csv_folder_round_trip(tmp_path):
    # pypsa-csv is a directory format: write through save(to_format="pypsa-csv"), read
    # back through parse via a folder path (powerio 0.3.3 folded the dedicated
    # read/write_pypsa_csv_folder tools into the bare verbs).
    out_dir = tmp_path / "pypsa_csv"
    w = powerio_mcp.save(to_format="pypsa-csv", out_path=str(out_dir), path=str(CASE9))
    assert w["files"], w
    assert (out_dir / "buses.csv").exists()
    r = powerio_mcp.parse(path=str(out_dir))
    assert r["summary"]["elements"]["buses"] == 9
    assert json.loads(r["json"])


def test_pypsa_csv_folder_accepts_transport(tmp_path):
    transport = powerio_mcp.parse(path=str(CASE9))["json"]
    out_dir = tmp_path / "from_json"
    w = powerio_mcp.save(to_format="pypsa-csv", out_path=str(out_dir), json=transport)
    assert (out_dir / "generators.csv").exists(), w


def test_read_pypsa_csv_missing_folder_maps_cleanly(tmp_path):
    with pytest.raises(ValueError):
        powerio_mcp.parse(path=str(tmp_path / "nope"))


def test_gridfm_round_trip(tmp_path):
    out_dir = tmp_path / "gfm"
    w = powerio_mcp.save(to_format="gridfm", out_path=str(out_dir), path=str(CASE9))
    assert w["files"], w
    r = powerio_mcp.parse(
        path=str(out_dir), from_format="gridfm", options={"scenario": 0}
    )
    assert r["summary"]["elements"]["buses"] == 9
    assert json.loads(r["json"])


def test_gridfm_missing_dir_maps_cleanly(tmp_path):
    with pytest.raises(ValueError):
        powerio_mcp.parse(path=str(tmp_path / "nope"), from_format="gridfm")


# ---------------------------------------------------------------------------
# PowerWorld .pwd display files. display is provided by the canonical
# powerio.mcp.server; these tests exercise the re-exported tool.
# ---------------------------------------------------------------------------

def test_display_decodes_pwd():
    r = powerio_mcp.display(str(ACTIVSG200_PWD))
    assert r["schema"] == "powerio.display"
    assert r["schema_version"] == "0.1"
    assert r["domain"] == "display"
    assert r["model"] == "display"
    assert r["source_format"] == "powerworld-pwd"
    assert r["canvas"]["width"] > 0 and r["canvas"]["height"] > 0
    subs = r["substations"]
    assert subs, "expected at least one substation"
    assert all(set(s) == {"number", "name", "x", "y"} for s in subs)
    assert any(s["name"] for s in subs)
    assert all(
        isinstance(s["x"], (int, float)) and isinstance(s["y"], (int, float))
        for s in subs
    )


def test_read_display_missing_file_maps_cleanly(tmp_path):
    with pytest.raises(ValueError):
        powerio_mcp.display(str(tmp_path / "nope.pwd"))


def test_read_display_garbage_file_maps_cleanly(tmp_path):
    bad = tmp_path / "garbage.pwd"
    bad.write_bytes(b"not a real display file\x00\x01\x02")
    with pytest.raises(ValueError):
        powerio_mcp.display(str(bad))


# ---------------------------------------------------------------------------
# OpenDSS consumes DSS files produced by PowerIO.
# ---------------------------------------------------------------------------

def _load_opendss_configuration(monkeypatch):
    opendss_dir = Path(__file__).resolve().parents[1] / "OpenDSS"
    monkeypatch.syspath_prepend(str(opendss_dir))

    fake_config = types.SimpleNamespace(
        compile_dss=lambda _path: None,
        circuit_readiness=lambda: {"ready": True},
    )
    fake_tools = types.SimpleNamespace(
        update_dss=lambda _dss: None,
        configuration=fake_config,
    )
    fake_dss_interface = types.SimpleNamespace(DSS=lambda: object())
    monkeypatch.setitem(
        sys.modules, "py_dss_toolkit", types.SimpleNamespace(dss_tools=fake_tools)
    )
    monkeypatch.setitem(sys.modules, "py_dss_interface", fake_dss_interface)

    for name in (
        "opendss_tools.configuration",
        "core.engine",
        "core.state",
        "utils.responses",
    ):
        sys.modules.pop(name, None)
    return importlib.import_module("opendss_tools.configuration")


def test_opendss_registration_excludes_distribution_wrapper(monkeypatch):
    configuration = _load_opendss_configuration(monkeypatch)
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("opendss-test")
    configuration.register_configuration_tools(mcp)
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert "compile_opendss_file" in names
    assert "clear_all_opendss_memory" in names
    assert "compile_distribution" not in names


def test_powerio_to_opendss_composition(monkeypatch, tmp_path):
    configuration = _load_opendss_configuration(monkeypatch)

    dss_path = tmp_path / "feeder.dss"
    save_result = powerio_mcp.save(
        out_path=str(dss_path),
        json=MINIMAL_BMOPF,
        json_format="bmopf-json",
    )
    assert save_result["path"] == str(dss_path)
    assert dss_path.exists()

    result = configuration.compile_opendss_file(str(dss_path))
    assert result["success"] is True
    assert result["payload"]["dss_file"] == str(dss_path)
