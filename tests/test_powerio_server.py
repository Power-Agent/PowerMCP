"""Consumer tests for PowerIO modules, solver adapters, and runner wiring."""

from __future__ import annotations

import asyncio
import builtins
import importlib
import json
import pickle
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("powerio", minversion="0.11.2")

import powerio  # noqa: E402
from powerio.mcp import server as powerio_mcp  # noqa: E402

from powermcp.registry import TOOLS  # noqa: E402

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


# 2-bus case whose pandapower emission raises no diagnostic, so the shared
# response tail carries an empty warnings list.
CLEAN_CASE = """function mpc = clean
mpc.version = '2';
mpc.baseMVA = 100.0;
mpc.bus = [
\t1 3 0 0 0 0 1 1.0 0.0 345.0 1 1.1 0.9;
\t2 1 50 10 0 0 1 1.0 0.0 345.0 1 1.1 0.9;
];
mpc.gen = [
\t1 60 10 0 0 1.0 100 1 100 0;
];
mpc.branch = [
\t1 2 0.01 0.1 0.0 250 250 250 0 0 1 -360 360;
];
"""


def test_parse_ir_round_trips():
    result = powerio_mcp.parse(path=str(CASE9))
    assert result["value_type"] == "powerio.BalancedNetwork"
    assert result["summary"]["elements"]["buses"] == 9
    document = json.loads(result["powerio_ir"])
    assert (document["schema"], document["version"]) == ("pio-ir", 2)
    assert powerio.deserialize(result["powerio_ir"].encode()).value.n_buses == 9


def test_registered_tools_are_canonical():
    tools = {tool.name: tool for tool in asyncio.run(powerio_mcp.mcp.list_tools())}
    assert {"parse", "emit", "summarize", "to_normalized", "calc_matrix",
            "diagnostics", "display", "about", "to_balanced", "to_balanced_report"} <= tools.keys()
    for name in ("summarize", "to_normalized", "calc_matrix"):
        props = tools[name].input_schema["properties"]
        assert {"path", "content", "powerio_ir", "format"} <= props.keys()
    props = tools["emit"].input_schema["properties"]
    assert {"format", "destination", "overwrite", "source_format"} <= props.keys()


def test_normalize_returns_dense_one_based_ids():
    result = powerio_mcp.to_normalized(path=str(CASE9))
    case = powerio.deserialize(result["powerio_ir"].encode()).value
    assert [b["id"] for b in case.buses] == list(range(1, 10))


@pytest.mark.parametrize("kind, shape", [("bprime", [9, 9]), ("lacpf", [18, 18]), ("weighted_laplacian", [9, 9])])
def test_matrices_accept_paths_and_ir(kind, shape):
    ir = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    direct = powerio_mcp.calc_matrix(kind, path=str(CASE9))
    restored = powerio_mcp.calc_matrix(kind, powerio_ir=ir)
    assert direct["shape"] == restored["shape"] == shape
    assert direct["data"] == restored["data"]
    assert direct["row"] == restored["row"]
    assert direct["col"] == restored["col"]
    assert type(direct["data"][0]) is float
    assert type(direct["row"][0]) is int
    assert direct["nnz"] > 0


def test_summary_fields():
    result = powerio_mcp.summarize(path=str(CASE9))
    assert result["domain"] == "transmission"
    assert result["electrical_model"] == "balanced"
    assert result["base_mva"] == 100.0
    assert result["source_format"] == "matpower"
    assert result["elements"]["buses"] == result["elements"]["branches"] == 9
    assert result["topology"]["connected_components"] == 1
    assert result["topology"]["connectivity_report"]
    assert isinstance(result["diagnostics"], list)


def test_input_and_matrix_validation():
    for kwargs in ({}, {"path": "x", "content": "y"}, {"powerio_ir": "{}"}):
        with pytest.raises(ValueError):
            powerio_mcp.summarize(**kwargs)
    with pytest.raises(ValueError, match="unknown matrix"):
        powerio_mcp.calc_matrix("nope", path=str(CASE9))


def test_emission_and_atomic_overwrite(tmp_path):
    ir = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    out = tmp_path / "case9.json"
    result = powerio_mcp.emit("powermodels-json", destination=str(out), powerio_ir=ir)
    assert result["path"] == str(out)
    assert len(json.loads(out.read_text())["bus"]) == 9
    before = out.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        powerio_mcp.emit("powermodels-json", destination=str(out), path=str(CASE9))
    assert out.read_bytes() == before
    powerio_mcp.emit("powermodels-json", destination=str(out), path=str(CASE9), overwrite=True)
    assert powerio.parse(out).value.n_buses == 9


def test_ir_diagnostics_and_same_format_fidelity():
    result = powerio_mcp.parse(path=str(CASE9))
    diagnostics = powerio_mcp.diagnostics(result["powerio_ir"])
    assert diagnostics["summary"]["status"] == "ok"
    assert isinstance(diagnostics["diagnostics"], list)
    emitted = powerio_mcp.emit("matpower", content=CASE9.read_text(), source_format="matpower")
    assert emitted["text"] == CASE9.read_text()


def test_pypsa_interchange_accepts_module(tmp_path):
    ir = powerio.serialize(powerio.parse(CASE9)).text
    out = tmp_path / "case9-module.nc"
    result = pypsa_mcp.import_case_from_json(ir, str(out))
    assert result["status"] == "success", result
    assert result["package"]["schema"] == "pio-ir"
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pandapower_interchange_accepts_module():
    panda_dir = str(TOOLS["pandapower"].resolve_server_dir())
    if panda_dir not in sys.path:
        sys.path.insert(0, panda_dir)
    import panda_mcp
    result = panda_mcp.load_network_from_json(powerio.serialize(powerio.parse(CASE9)).text)
    assert result["status"] == "success", result
    assert result["package"]["schema"] == "pio-ir"
    assert len(panda_mcp._current_net.bus) == 9


def test_pandapower_response_states_an_empty_warnings_list():
    """The shared response tail reaches the caller whole, empty lists included.

    A caller reads ``warnings`` the same way from every adapter, so a load that
    raised nothing states an empty list rather than dropping the key.
    """
    panda_dir = str(TOOLS["pandapower"].resolve_server_dir())
    if panda_dir not in sys.path:
        sys.path.insert(0, panda_dir)
    import panda_mcp

    module = powerio.parse(CLEAN_CASE.encode(), format="matpower", name="clean.m")
    result = panda_mcp.load_network_from_json(powerio.serialize(module).text)
    assert result["status"] == "success", result
    assert result["warnings"] == []
    assert result["diagnostics"] == []
    assert result["value_type"] == "powerio.BalancedNetwork"
    assert result["selection"] == {}


def test_solver_interchange_requires_explicit_state(tmp_path):
    value = powerio.parse(CASE9).value
    series = powerio.TimeSeries([value, value], time_points=[powerio.TimePoint("base", duration_seconds=3600), powerio.TimePoint("later", duration_seconds=3600)])
    ir = powerio.serialize(powerio.PioModule.from_value(series)).text
    rejected = pypsa_mcp.import_case_from_json(ir, str(tmp_path / "unselected.nc"))
    assert rejected["status"] == "error"
    assert "time_index" in rejected["message"]
    selected = pypsa_mcp.import_case_from_json(ir, str(tmp_path / "selected.nc"), time_index=1)
    assert selected["status"] == "success", selected
    assert selected["package"]["selection"]["time_index"] == 1


def test_solver_interchange_rejects_unavailable_study_commit(tmp_path):
    ir = powerio.serialize(powerio.parse(CASE9)).text
    out = tmp_path / "study.nc"
    result = pypsa_mcp.import_case_from_json(ir, str(out), study_commit=0)
    assert result["status"] == "error"
    assert "Study" in result["message"]
    assert not out.exists()


def test_pypsa_import_case_from_any(tmp_path):
    out = tmp_path / "case9.nc"
    r = pypsa_mcp.import_case_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["network_file"] == str(out)
    assert r["info"]["buses"] == 9
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pypsa_import_case_from_json(tmp_path):
    transport = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    out = tmp_path / "case9.nc"
    r = pypsa_mcp.import_case_from_json(transport, str(out))
    assert r["status"] == "success", r
    assert len(pypsa.Network(str(out)).buses) == 9


def test_pypsa_import_preserves_supported_generator_costs(tmp_path):
    out = tmp_path / "costs.nc"
    result = pypsa_mcp.import_case_from_any(str(CASE9), str(out))
    assert result["status"] == "success", result
    generators = pypsa.Network(str(out)).generators
    assert (generators.marginal_cost != 0).all()
    assert generators.start_up_cost.tolist() == pytest.approx([1500, 2000, 3000])
    assert any("constant polynomial cost" in warning for warning in result["warnings"])


def test_pypsa_import_applies_generator_voltage_targets_to_buses(tmp_path):
    out = tmp_path / "voltage-targets.nc"
    result = pypsa_mcp.import_case_from_any(str(CASE9), str(out))
    assert result["status"] == "success", result

    network = pypsa.Network(str(out))
    assert network.buses.loc[["1", "2", "3"], "v_mag_pu_set"].tolist() == pytest.approx(
        [1.04, 1.025, 1.025]
    )


def test_pypsa_create_network_uses_default_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = pypsa_mcp.create_network("empty")

    assert result["status"] == "success", result
    network = pypsa.Network(result["network_file"])
    assert len(network.snapshots) == 1


def _write_feasible_pypsa_network(path: Path, *, extendable: bool = False) -> None:
    network = pypsa.Network()
    network.add("Bus", "bus")
    network.add("Load", "load", bus="bus", p_set=10.0)
    network.add(
        "Generator",
        "generator",
        bus="bus",
        carrier="gas",
        p_nom=0.0 if extendable else 20.0,
        p_nom_extendable=extendable,
        capital_cost=5.0,
        marginal_cost=10.0,
    )
    network.export_to_netcdf(path)


def test_pypsa_optimize_network_uses_modern_optimizer(tmp_path):
    path = tmp_path / "dispatch.nc"
    _write_feasible_pypsa_network(path)

    result = pypsa_mcp.optimize_network(str(path))

    assert result["status"] == "ok", result
    assert result["termination_condition"] == "optimal"
    assert result["objective"] == pytest.approx(100.0)
    assert result["generators"]["generator"]["p"] == pytest.approx(10.0)


def test_pypsa_optimize_investment_uses_modern_optimizer(tmp_path):
    path = tmp_path / "investment.nc"
    _write_feasible_pypsa_network(path, extendable=True)

    result = pypsa_mcp.optimize_investment(str(path), carriers=["gas"])

    assert result["status"] == "ok", result
    assert result["termination_condition"] == "optimal"
    assert result["investments"]["generators"]["generator"][
        "p_nom_opt"
    ] == pytest.approx(10.0)


def test_pypsa_legacy_optimizer_options_fail_clearly(tmp_path):
    path = tmp_path / "legacy-options.nc"
    path.write_bytes(b"")

    formulation = pypsa_mcp.optimize_network(str(path), formulation="angles")
    pyomo = pypsa_mcp.optimize_network(str(path), pyomo=True)

    assert formulation["status"] == "error"
    assert "legacy LOPF formulations" in formulation["message"]
    assert pyomo["status"] == "error"
    assert "legacy Pyomo" in pyomo["message"]


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
    # The absent case sits inside an allowed root, so the refusal states what is
    # wrong with the file rather than where it is.
    r = pypsa_mcp.import_case_from_any(
        str(tmp_path / "missing.m"), str(tmp_path / "x.nc")
    )
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


def test_pypsa_network_name_is_confined(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.nc"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    with pytest.raises(ValueError, match="outside allowed MCP roots"):
        pypsa_mcp.get_network_info(str(outside))


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
def test_pypsa_csv_import_preflights_the_complete_tree(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    dataset = allowed / "network"
    outside = tmp_path / "outside.csv"
    dataset.mkdir(parents=True)
    outside.write_text("name\nsecret\n")
    (dataset / "buses.csv").symlink_to(outside)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = pypsa_mcp.import_from_csv_folder(
        str(dataset), str(allowed / "network.nc")
    )
    assert result["status"] == "error"
    assert "outside its allowed MCP root" in result["message"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
def test_pypsa_network_read_preflights_a_csv_tree(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    dataset = allowed / "network"
    outside = tmp_path / "outside.csv"
    dataset.mkdir(parents=True)
    outside.write_text("name\nsecret\n")
    (dataset / "buses.csv").symlink_to(outside)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    with pytest.raises(ValueError, match="outside its allowed MCP root"):
        pypsa_mcp.get_network_info(str(dataset))


def test_pypsa_csv_import_checks_an_explicit_output(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    dataset = allowed / "network"
    dataset.mkdir(parents=True)
    outside = tmp_path / "outside.nc"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = pypsa_mcp.import_from_csv_folder(str(dataset), str(outside))

    assert result["status"] == "error"
    assert "outside allowed MCP roots" in result["message"]


def test_pypsa_csv_import_keeps_the_checked_legacy_default(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    dataset = allowed / "network"
    dataset.mkdir(parents=True)
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = pypsa_mcp.import_from_csv_folder(str(dataset))

    assert result["status"] == "error"
    assert "outside allowed MCP roots" in result["message"]


def test_pypsa_csv_export_is_staged_and_preserves_unrelated_files(tmp_path):
    network_file = tmp_path / "network.nc"
    network = pypsa.Network()
    network.add("Bus", "bus")
    network.export_to_netcdf(network_file)

    output = tmp_path / "csv"
    output.mkdir()
    (output / "keep.txt").write_text("keep")
    result = pypsa_mcp.export_to_csv_folder(str(network_file), str(output))

    assert result["status"] == "success", result
    assert (output / "keep.txt").read_text() == "keep"
    assert (output / "buses.csv").is_file()


def test_registry_entry():
    t = TOOLS["powerio"]
    assert t.kind == "open-source"
    assert t.extra is None  # promoted to a core dependency (issue #30)
    assert t.windows_only is False
    assert t.probe == "powerio"
    # The server ships in powerio's own wheel, so there is no bundled dir here
    # and no local file enumerating powerio's registered tools.
    assert t.run_kind == "package"
    assert t.module == "powerio.mcp"
    assert t.server_dir is None
    with pytest.raises(ValueError, match="own distribution"):
        t.resolve_server_dir()
    assert not (Path(__file__).resolve().parents[1] / "powerio").exists()


@pytest.fixture()
def record_mcp_run(monkeypatch):
    calls = []

    def fake_run(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("mcp.server.mcpserver.MCPServer.run", fake_run, raising=True)
    return calls


def test_launch_powerio_runs_once(record_mcp_run):
    from powermcp import runner

    runner.launch("powerio")
    assert len(record_mcp_run) == 1
    args, kwargs = record_mcp_run[0]
    # powerio's own entry point takes the SDK default rather than naming it.
    transport = kwargs.get("transport") or (args[0] if args else "stdio")
    assert transport == "stdio"


def test_inline_emission_stages_no_temp_files(monkeypatch):
    # `emit` writes an in-memory result when no destination names a file, so
    # touching tempfile would mean it staged through disk.
    import tempfile

    def boom(*args, **kwargs):
        raise AssertionError("inline conversion must not create temp files")

    monkeypatch.setattr(tempfile, "mkstemp", boom)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", boom)
    r = powerio_mcp.emit(
        format="psse", content=CASE9.read_text(), source_format="matpower"
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


def test_pypsa_import_preserves_out_of_service_branch(tmp_path):
    src = tmp_path / "oos.m"
    src.write_text(OOS_CASE)
    out = tmp_path / "oos.nc"
    r = pypsa_mcp.import_case_from_any(str(src), str(out))
    assert r["status"] == "success", r
    lines = pypsa.Network(str(out)).lines
    assert lines.shape[0] == 2
    assert lines.active.tolist().count(False) == 1


def test_pypsa_import_preserves_out_of_service_generator(tmp_path):
    src = tmp_path / "oos.m"
    src.write_text(OOS_CASE)
    r = pypsa_mcp.import_case_from_any(str(src), str(tmp_path / "g.nc"))
    assert r["status"] == "success", r
    generators = pypsa.Network(str(tmp_path / "g.nc")).generators
    assert generators.shape[0] == 2
    assert generators.active.tolist().count(False) == 1


def test_pandapower_bridge_honors_branch_status(tmp_path):
    # PowerIO's native pandapower writer keeps the OOS row and its status.
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


def test_pandapower_pickle_input_is_rejected_without_execution(tmp_path):
    panda_dir = str(TOOLS["pandapower"].resolve_server_dir())
    if panda_dir not in sys.path:
        sys.path.insert(0, panda_dir)
    import panda_mcp  # noqa: E402

    marker = tmp_path / "pickle-executed"

    class Payload:
        def __reduce__(self):
            statement = f"open({str(marker)!r}, 'w').write('executed')"
            return builtins.exec, (statement,)

    payload = tmp_path / "network.p"
    payload.write_bytes(pickle.dumps(Payload()))

    result = panda_mcp.load_network(str(payload))

    assert result["status"] == "error"
    assert "Use a .json file" in result["message"]
    assert not marker.exists()


def test_matrix_laplacian():
    m = powerio_mcp.calc_matrix("weighted_laplacian", path=str(CASE9))
    assert m["format"] == "coo"
    assert m["shape"] == [9, 9]


def test_matrix_bad_json_raises_valueerror():
    with pytest.raises(ValueError):
        powerio_mcp.calc_matrix("bprime", powerio_ir="{not valid json")


def test_emit_oserror_normalizes_to_valueerror(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(powerio, "emit", boom)
    with pytest.raises(ValueError, match="disk full"):
        powerio_mcp.emit("psse", content=CASE9.read_text(), source_format="matpower")



def test_allowed_roots_rejects_read_outside_root(tmp_path, monkeypatch):
    # The session fixture names the repository and the temporary tree for every
    # other test in this file. This test names its own root, so both the refusal
    # and the admission run against a directory the test controls.
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside" / "case9.m"
    outside.parent.mkdir()
    outside.write_text(CASE9.read_text())
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(ValueError, match="outside allowed MCP roots"):
        powerio_mcp.parse(path=str(outside))


def test_allowed_roots_admits_read_inside_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    case = root / "case9.m"
    case.write_text(CASE9.read_text())
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    r = powerio_mcp.parse(path=str(case))
    assert r["value_type"] == "powerio.BalancedNetwork"


def test_allowed_roots_rejects_write_outside_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    outside_out = tmp_path / "outside" / "case9.raw"
    outside_out.parent.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(ValueError, match="outside allowed MCP roots"):
        powerio_mcp.emit(
            destination=str(outside_out), content=CASE9.read_text(), format="psse", source_format="matpower"
        )


def test_allowed_roots_admits_write_inside_root(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    out = root / "case9.raw"
    r = powerio_mcp.emit(destination=str(out), content=CASE9.read_text(), format="psse", source_format="matpower")
    assert r["path"] == str(out)
    assert out.exists()


def test_unreadable_file_maps_cleanly(tmp_path):
    # PermissionError must be reported as the documented ValueError shape, like
    # FileNotFoundError, not leak raw through the tool. (Ported from the
    # canonical server's suite at powerio 0.1.1.)
    import os

    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("permission bits are not enforceable here")
    locked = tmp_path / "locked.m"
    locked.write_text("function mpc = x\n")
    locked.chmod(0o000)
    try:
        with pytest.raises(ValueError, match="Permission denied"):
            powerio_mcp.emit(format="psse", path=str(locked))
        with pytest.raises(ValueError, match="Permission denied"):
            powerio_mcp.summarize(path=str(locked))
    finally:
        locked.chmod(0o644)


def test_wrong_schema_ir_maps_cleanly():
    for bad in ("{}", "[]", "null", '{"buses": "nope"}'):
        with pytest.raises(ValueError):
            powerio_mcp.calc_matrix("bprime", powerio_ir=bad)



def test_legacy_model_json_requires_migration():
    from powermcp.solver_case import resolve_solver_case
    with pytest.raises(ValueError):
        resolve_solver_case(network_json='{"model_kind":"balanced","model":{}}')



# ---------------------------------------------------------------------------
# ANDES bridge tests
#
# The andes_mcp fixture (shared with test_andes_server.py) lives in
# conftest.py; it skips via pytest.importorskip("andes") when andes isn't
# installed.
# ---------------------------------------------------------------------------

def test_andes_load_network_from_any(tmp_path, andes_mcp):
    out = tmp_path / "case9.m"
    r = andes_mcp.load_network_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["case_file"] == str(out)
    assert r["info"]["buses"] == 9


def test_andes_load_network_from_json(tmp_path, andes_mcp):
    transport = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    out = tmp_path / "case9_from_json.m"
    r = andes_mcp.load_network_from_json(transport, str(out))
    assert r["status"] == "success", r
    assert out.exists()
    assert r["info"]["buses"] == 9


def test_andes_case_file_replaces_an_existing_case(tmp_path, andes_mcp):
    out = tmp_path / "case9.m"
    out.write_text("stale", encoding="utf-8")
    r = andes_mcp.load_network_from_any(str(CASE9), str(out))
    assert r["status"] == "success", r
    assert "mpc.bus" in out.read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlink semantics")
def test_andes_case_file_is_never_written_through_a_link(tmp_path, andes_mcp):
    """The staged install replaces one regular file and refuses anything else."""
    target = tmp_path / "target.m"
    target.write_text("keep", encoding="utf-8")
    out = tmp_path / "case9.m"
    out.symlink_to(target)
    r = andes_mcp.load_network_from_any(str(CASE9), str(out))
    assert r["status"] == "error"
    assert "regular file" in r["message"]
    assert target.read_text(encoding="utf-8") == "keep"


def test_andes_load_missing_file(tmp_path, andes_mcp):
    r = andes_mcp.load_network_from_any(str(tmp_path / "missing.m"), str(tmp_path / "x.m"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


# ---------------------------------------------------------------------------
# pandapower-json plus folder and Parquet formats routed through generic verbs.
# ---------------------------------------------------------------------------

def test_emit_to_pandapower_json():
    r = powerio_mcp.emit(format="pandapower-json", path=str(CASE9))
    assert r["text"]
    assert json.loads(r["text"])  # well-formed JSON


def test_pandapower_json_round_trips_through_transport():
    # pandapower-json is a plain text format, so it flows through the existing
    # save/parse tools with no dedicated tool.
    transport = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    out = powerio_mcp.parse(
        content=powerio_mcp.emit(format="pandapower-json", path=str(CASE9))[
            "text"
        ],
        format="pandapower-json",
    )
    assert json.loads(out["powerio_ir"])
    assert json.loads(transport)


def test_pypsa_csv_folder_round_trip(tmp_path):
    # pypsa-csv is a directory format: write through save(format="pypsa-csv"), read
    # back through parse via a folder path (powerio 0.3.3 folded the dedicated
    # read/write_pypsa_csv_folder tools into the bare verbs).
    out_dir = tmp_path / "pypsa_csv"
    w = powerio_mcp.emit(format="pypsa-csv", destination=str(out_dir), path=str(CASE9))
    assert w["files"], w
    assert (out_dir / "buses.csv").exists()
    r = powerio_mcp.parse(path=str(out_dir))
    assert r["summary"]["elements"]["buses"] == 9
    assert json.loads(r["powerio_ir"])


def test_pypsa_csv_folder_accepts_transport(tmp_path):
    transport = powerio_mcp.parse(path=str(CASE9))["powerio_ir"]
    out_dir = tmp_path / "from_json"
    w = powerio_mcp.emit(format="pypsa-csv", destination=str(out_dir), powerio_ir=transport)
    assert (out_dir / "generators.csv").exists(), w


def test_read_pypsa_csv_missing_folder_maps_cleanly(tmp_path):
    with pytest.raises(ValueError):
        powerio_mcp.parse(path=str(tmp_path / "nope"))


def test_gridfm_round_trip(tmp_path):
    out_dir = tmp_path / "gfm"
    emitted = powerio_mcp.emit("gridfm", destination=str(out_dir), path=str(CASE9))
    assert emitted["files"]
    parsed = powerio_mcp.parse(path=str(out_dir), format="gridfm")
    assert parsed["summary"]["collection"] == "ScenarioSet"
    scenarios = parsed["summary"]["scenarios"]
    assert len(scenarios) == 1
    restored = powerio.deserialize(parsed["powerio_ir"].encode()).value
    scenario = restored[scenarios[0]["id"]]
    assert scenario.n_buses == 9


def test_gridfm_missing_dir_maps_cleanly(tmp_path):
    with pytest.raises(ValueError):
        powerio_mcp.parse(path=str(tmp_path / "nope"), format="gridfm")


# ---------------------------------------------------------------------------
# PowerWorld .pwd display files. display is provided by the canonical
# powerio.mcp.server; these tests exercise the re-exported tool.
# ---------------------------------------------------------------------------

def test_display_decodes_pwd():
    r = powerio_mcp.display(str(ACTIVSG200_PWD))
    assert r["format"] == "powerworld-pwd"
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
    from mcp.server.mcpserver import MCPServer as FastMCP

    mcp = FastMCP("opendss-test")
    configuration.register_configuration_tools(mcp)
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert "compile_opendss_file" in names
    assert "clear_all_opendss_memory" in names
    assert "compile_distribution" not in names


def test_powerio_to_opendss_composition(monkeypatch, tmp_path):
    configuration = _load_opendss_configuration(monkeypatch)

    dss_dir = tmp_path / "feeder"
    save_result = powerio_mcp.emit(
        destination=str(dss_dir),
        format="opendss",
        content=MINIMAL_BMOPF,
        source_format="bmopf-json",
    )
    assert save_result["dir"] == str(dss_dir)
    dss_path = next(Path(path) for path in save_result["files"] if path.endswith(".dss"))
    assert dss_path.exists()

    result = configuration.compile_opendss_file(str(dss_path))
    assert result["status"] == "success"
    assert result["payload"]["dss_file"] == str(dss_path)


def test_opendss_without_containment_does_not_scan_the_parent_tree(
    monkeypatch, tmp_path
):
    configuration = _load_opendss_configuration(monkeypatch)
    dss_path = tmp_path / "feeder.dss"
    dss_path.write_text("Clear")
    monkeypatch.setattr(configuration, "allowed_roots", lambda: ())
    monkeypatch.setattr(
        configuration,
        "checked_read_tree",
        lambda *_a, **_k: pytest.fail("unconfigured OpenDSS must not scan siblings"),
    )

    result = configuration.compile_opendss_file(str(dss_path))

    assert result["status"] == "success"


# ---- 0.11 boundary: powerio_ir, typed edits, lowering, response tail -----------


def test_adapters_take_powerio_ir_and_report_the_shared_tail(tmp_path):
    ir = powerio.serialize(powerio.parse(CASE9)).text
    out = tmp_path / "case9.nc"
    result = pypsa_mcp.import_case_from_json(powerio_ir=ir, output_path=str(out))
    assert result["status"] == "success", result
    assert result["value_type"] == "powerio.BalancedNetwork"
    assert result["selection"] == {}
    assert result["fidelity"] in {"canonical", "exact_same_format"}
    assert isinstance(result["diagnostics"], list)
    assert result["package"]["schema"] == "pio-ir"
    both = pypsa_mcp.import_case_from_json(powerio_ir=ir, network_json=ir, output_path=str(tmp_path / "x.nc"))
    assert both["status"] == "error" and "not both" in both["message"]
    missing = pypsa_mcp.import_case_from_json(powerio_ir=ir)
    assert missing["status"] == "error" and "output_path" in missing["message"]


def test_typed_edits_reach_the_pandapower_model():
    panda_dir = str(TOOLS["pandapower"].resolve_server_dir())
    if panda_dir not in sys.path:
        sys.path.insert(0, panda_dir)
    import panda_mcp
    base = powerio.parse(CASE9).value
    load_id = base.loads[0].get("uid") or "loads:0"
    ir = powerio.serialize(powerio.parse(CASE9)).text
    edits = json.dumps([
        {"op": "set_load_active_power", "load": load_id, "mw": 91.5},
        {"op": "set_branch_in_service", "branch": base.branches[0].get("uid") or "branches:0", "in_service": False},
    ])
    result = panda_mcp.load_network_from_json(powerio_ir=ir, edits=edits)
    assert result["status"] == "success", result
    assert result["edits"]["connectivity_changed"] is True
    assert {change["component_type"] for change in result["edits"]["changes"]} == {"load", "branch"}
    assert 91.5 in set(round(float(p), 3) for p in panda_mcp._current_net.load["p_mw"])
    assert not panda_mcp._current_net.line["in_service"].all() or not panda_mcp._current_net.trafo["in_service"].all()
    rejected = panda_mcp.load_network_from_json(powerio_ir=ir, edits='[{"op": "teleport"}]')
    assert rejected["status"] == "error" and "unknown op" in rejected["message"]


def test_multiconductor_input_needs_the_explicit_lowering_flag(tmp_path):
    feeder = Path(__file__).resolve().parent / "data" / "opendss" / "fourwire_linecode.dss"
    refused = pypsa_mcp.import_case_from_any(str(feeder), str(tmp_path / "refused.nc"))
    assert refused["status"] == "error" and "to_balanced" in refused["message"]
    lowered = pypsa_mcp.import_case_from_any(
        str(feeder), str(tmp_path / "lowered.nc"), to_balanced=True, base_mva=1.0
    )
    assert lowered["status"] == "success", lowered
    assert lowered["value_type"] == "powerio.MulticonductorNetwork"
    assert "ready" in lowered["lowering"]
    assert (tmp_path / "lowered.nc").exists()


def test_matrix_names_its_axes():
    matrix = powerio_mcp.calc_matrix("bprime", path=str(CASE9))
    assert matrix["shape"] == [9, 9]
    assert matrix["row_ids"] == matrix["col_ids"]
    assert len(matrix["row_ids"]) == 9
