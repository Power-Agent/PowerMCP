"""Server tools called in process: schemas, error mapping, path containment."""
import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

import onsset_mcp as server
from test_inputs import settlements, write

REQUIRED = {"start_year": 2024, "end_year": 2030, "end_year_pop": 1000, "urban_ratio_end_year": 0.4}
EXPECTED_TOOLS = {"get_server_info", "check_environment", "list_input_files", "describe_parameters",
                  "validate_parameters", "validate_inputs", "start_calibration", "start_scenario_run",
                  "get_run_status", "cancel_run", "list_runs", "get_run_results", "inspect_result_columns",
                  "summarize_results_by", "compare_runs"}


def test_tools_registered_with_schemas():
    tools = asyncio.run(server.mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS
    for t in tools:
        assert t.description and t.input_schema["type"] == "object" and t.output_schema
    run = next(t for t in tools if t.name == "start_scenario_run")
    assert set(run.input_schema["required"]) == {"input_csv", "pv_csv", "wind_csv", "mv_lines", "params",
                                                 "scenario_name"}


def test_server_info(workspace):
    ws, data = workspace
    info = server.get_server_info()
    assert info["workspace"] == str(ws.resolve())
    assert str(data.resolve()) in info["allowed_input_roots"]


def test_describe_and_validate_parameters():
    scen = server.describe_parameters("scenario")
    assert scen["required"] == ["start_year", "end_year", "end_year_pop", "urban_ratio_end_year"]
    calib = server.describe_parameters("calibration")
    assert "pop_start_year" in calib["required"]
    ok = server.validate_parameters(REQUIRED)
    assert ok["valid"] and ok["time_steps"] == [{"year": 2030, "electrification_target": 1.0, "step_years": 6}]
    assert "diesel_price" in ok["defaulted"]
    bad = server.validate_parameters({**REQUIRED, "grid_losses": 2, "foo": 1})
    assert not bad["valid"]
    assert any(e.startswith("grid_losses") for e in bad["errors"])
    assert any(e.startswith("foo") for e in bad["errors"])


def test_validate_inputs_and_containment(workspace, tmp_path):
    ws, data = workspace
    path = write(settlements(), data / "s.csv")
    r = server.validate_inputs(str(path), "calibration")
    assert r["ok"] and r["files"]["input_csv"] == str(path.resolve())
    outside = write(settlements(), tmp_path / "outside.csv")
    with pytest.raises(ToolError, match="outside the allowed directories"):
        server.validate_inputs(str(outside), "calibration")
    with pytest.raises(ToolError, match="file not found"):
        server.validate_inputs(str(data / "missing.csv"), "calibration")
    with pytest.raises(ToolError, match="pv_csv is required"):
        server.validate_inputs(str(path), "scenario")
    with pytest.raises(ToolError, match="outside the allowed"):
        server.validate_inputs(str(data / ".." / "outside.csv"), "calibration")


@pytest.mark.parametrize("end_year_pop, ok, growth", [(500, False, None), (800, True, 0.01772)])
def test_population_decline_is_an_input_error(end_year_pop, ok, growth):
    rep = {"info": {"start_year_population": 720.0, "start_year_urban_ratio": 0.33}, "errors": [], "warnings": []}
    server._check_demographics(rep, {**REQUIRED, "end_year_pop": end_year_pop})
    assert rep["ok"] is ok
    if not ok:
        assert "below the calibrated start-year population" in rep["errors"][0]
    else:
        assert rep["info"]["implied_annual_population_growth"] == pytest.approx(growth, abs=1e-4)


def test_start_refuses_invalid_requests(workspace):
    ws, data = workspace
    path = write(settlements(), data / "s.csv")
    with pytest.raises(ToolError, match="Invalid parameters: end_year"):
        server.start_scenario_run(str(path), "a", "b", "c", {"start_year": 2024}, "s1")
    with pytest.raises(ToolError, match="Invalid run name"):
        server.start_scenario_run(str(path), "a", "b", "c", REQUIRED, "../evil")
    calib = {"start_year": 2024, "pop_start_year": 1000, "urban_ratio_start_year": 0.3,
             "grid_elec_ratio_start_year": 0.5, "grid_urban_elec_ratio": 0.8, "grid_rural_elec_ratio": 0.3}
    no_mg = write(settlements().drop(columns=["MGDist"]), data / "nomg.csv")
    with pytest.raises(ToolError, match="Input validation failed: MGDist"):
        server.start_calibration(str(no_mg), calib, "c1")
    assert not (ws / "c1").exists()


def test_result_tools_report_missing_runs(workspace):
    with pytest.raises(ToolError, match="No run named 'ghost'"):
        server.get_run_results("ghost")
    with pytest.raises(ToolError, match="No run named"):
        server.get_run_status("ghost")
    with pytest.raises(ToolError, match="log_lines"):
        server.get_run_status("ghost", log_lines=1000)
    assert server.list_runs()["runs"] == []


def test_list_input_files(workspace):
    ws, data = workspace
    write(settlements(), data / "s.csv")
    (data / "pv.csv").write_text("# Renewables.ninja Weather (hourly data)\nx\n")
    (data / "notes.txt").write_text("ignored")
    listing = server.list_input_files(str(data))
    roles = {f["path"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]: f["role"] for f in listing["files"]}
    assert roles == {"s.csv": "settlements (calibrated)", "pv.csv": "pv_hourly (renewables.ninja weather)"}
    with pytest.raises(ToolError, match="max_depth"):
        server.list_input_files(str(data), max_depth=10)


def test_unexpected_exceptions_become_tool_errors():
    @server.guarded
    def boom():
        raise KeyError("x")
    with pytest.raises(ToolError, match="KeyError"):
        boom()
