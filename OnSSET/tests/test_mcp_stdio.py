"""The server over a real stdio MCP session.

``test_protocol`` needs only the MCP SDK. The ``slow`` tests drive the whole workflow through
the protocol on real data: a calibration of the Djibouti extract shipped with OnSSET, and
scenario runs on a ~4400-settlement window of the calibrated Uganda input (about a minute each).
"""
import asyncio
import json
import os
import sys
import time

import pandas as pd
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import DJIBOUTI_CSV, HAVE_UGANDA, SERVER_DIR, UGANDA_FILES

TIMEOUT = 120.0
SCENARIO = {"start_year": 2024, "end_year": 2030, "end_year_pop": 6_500_000, "urban_ratio_end_year": 0.9,
            "intermediate_targets": {"2027": 0.92}}


def run_session(env, steps):
    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER_DIR / "onsset_mcp.py")],
                                       env={**os.environ, **env}, cwd=str(SERVER_DIR))
        with open(os.devnull, "w") as errlog:
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=TIMEOUT) as session:
                    init = await asyncio.wait_for(session.initialize(), TIMEOUT)
                    return await steps(session, init)
    return asyncio.run(go())


def payload(result):
    assert not result.is_error, result.content[0].text
    if result.structured_content is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


def error_text(result):
    assert result.is_error
    return result.content[0].text


def env_for(tmp_path, data=None):
    env = {"ONSSET_WORKSPACE": str(tmp_path / "ws")}
    if data:
        env["ONSSET_ALLOWED_ROOTS"] = str(data)
    return env


def test_protocol(tmp_path):
    async def steps(session, init):
        out = {"server": init.server_info.name, "version": init.server_info.version}
        out["tools"] = sorted(t.name for t in (await session.list_tools()).tools)
        out["valid"] = payload(await session.call_tool("validate_parameters", {
            "params": {"start_year": 2024, "end_year": 2050, "end_year_pop": 1e6, "urban_ratio_end_year": 0.4}}))
        out["invalid"] = payload(await session.call_tool("validate_parameters", {"params": {"start_year": 1}}))
        out["missing_arg"] = error_text(await session.call_tool("validate_inputs", {}))
        out["bad_type"] = error_text(await session.call_tool("get_run_status", {"run_name": "x", "log_lines": "a"}))
        out["tool_error"] = error_text(await session.call_tool("get_run_results", {"run_name": "ghost"}))
        out["bad_path"] = error_text(await session.call_tool("validate_inputs", {"input_csv": "C:/Windows/win.ini"}))
        out["unknown_tool"] = error_text(await session.call_tool("no_such_tool", {}))
        out["after_errors"] = payload(await session.call_tool("get_server_info", {}))
        out["runs"] = payload(await session.call_tool("list_runs", {}))
        return out

    out = run_session(env_for(tmp_path), steps)
    assert out["server"] == "onsset" and out["version"] == "0.1.0"
    assert len(out["tools"]) == 15 and "start_scenario_run" in out["tools"]
    assert out["valid"]["valid"] and out["valid"]["params"]["diesel_price"] == 1.43
    assert not out["invalid"]["valid"]
    assert "input_csv" in out["missing_arg"]
    assert "log_lines" in out["bad_type"]
    assert "No run named 'ghost'" in out["tool_error"]
    assert "outside the allowed directories" in out["bad_path"]
    assert "no_such_tool" in out["unknown_tool"]
    assert out["after_errors"]["server"] == "onsset"
    assert out["runs"]["runs"] == []


async def wait_for(session, name, timeout=900):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = payload(await session.call_tool("get_run_status", {"run_name": name, "log_lines": 5}))
        if status["status"] != "running":
            return status
        await asyncio.sleep(2)
    raise AssertionError(f"run {name} did not finish in {timeout} s")


@pytest.fixture(scope="module")
def kampala(tmp_path_factory):
    """Settlements within 0.25 deg of (32.58 E, 0.32 N), cut from the calibrated Uganda input."""
    data = tmp_path_factory.mktemp("data")
    df = pd.read_csv(UGANDA_FILES["input_csv"])
    w = 0.25
    df = df[df.X_deg.between(32.58 - w, 32.58 + w) & df.Y_deg.between(0.32 - w, 0.32 + w)]
    path = data / "kampala_subset.csv"
    df.to_csv(path, index=False)
    return data, path


@pytest.mark.slow
@pytest.mark.skipif(not HAVE_UGANDA, reason="Uganda inputs not available")
def test_scenario_workflow_end_to_end(tmp_path, kampala):
    data, subset = kampala
    files = {"input_csv": str(subset), **{k: str(UGANDA_FILES[k]) for k in ("pv_csv", "wind_csv", "mv_lines")}}

    async def steps(session, init):
        out = {}
        env = payload(await session.call_tool("check_environment", {}))
        assert env["ok"], env["problems"]
        listing = payload(await session.call_tool("list_input_files", {}))
        roles = {f["role"] for f in listing["files"]}
        assert {"pv_hourly (renewables.ninja weather)", "wind_hourly (renewables.ninja wind)"} <= roles

        v = payload(await session.call_tool("validate_inputs", {**files, "params": SCENARIO}))
        assert v["ok"], v["reports"]
        out["validation"] = v
        bad = payload(await session.call_tool("validate_inputs", {**files, "params": {**SCENARIO,
                                                                                        "end_year_pop": 1e6}}))
        assert not bad["ok"]

        args = {**files, "params": SCENARIO, "scenario_name": "base"}
        started = payload(await session.call_tool("start_scenario_run", args))
        assert started["status"] == "running"
        busy = error_text(await session.call_tool("start_scenario_run", {**args, "scenario_name": "other"}))
        assert "already in progress" in busy
        out["base_status"] = await wait_for(session, "base")
        exists = error_text(await session.call_tool("start_scenario_run", args))
        assert "overwrite=true" in exists

        cheap_pv = {**SCENARIO, "pv_cost": 700, "battery_cost": 300, "diesel_price": 2.0}
        payload(await session.call_tool("start_scenario_run", {**args, "params": cheap_pv,
                                                                "scenario_name": "cheap_pv"}))
        out["cheap_status"] = await wait_for(session, "cheap_pv")

        out["results"] = payload(await session.call_tool("get_run_results", {"run_name": "base"}))
        out["columns"] = payload(await session.call_tool("inspect_result_columns", {"run_name": "base"}))
        out["by_urban"] = payload(await session.call_tool("summarize_results_by", {"run_name": "base",
                                                                                   "group_by": "IsUrban"}))
        out["by_urban_2027"] = payload(await session.call_tool("summarize_results_by", {
            "run_name": "base", "group_by": "IsUrban", "year": 2027}))
        out["compare"] = payload(await session.call_tool("compare_runs", {"run_names": ["base", "cheap_pv"]}))

        payload(await session.call_tool("start_scenario_run", {**args, "scenario_name": "to_cancel"}))
        out["cancelled"] = payload(await session.call_tool("cancel_run", {"run_name": "to_cancel"}))
        out["runs"] = payload(await session.call_tool("list_runs", {}))
        out["cancelled_results"] = error_text(await session.call_tool("get_run_results", {"run_name": "to_cancel"}))
        return out

    out = run_session(env_for(tmp_path, data), steps)
    info = out["validation"]["reports"][0]["info"]
    assert info["n_settlements"] == 4385

    assert out["base_status"]["status"] == "succeeded", out["base_status"]
    assert out["cheap_status"]["status"] == "succeeded", out["cheap_status"]

    r = out["results"]
    assert r["years"] == [2027, 2030]
    rates = r["electrification_rate"]
    assert rates["2030"] == pytest.approx(1.0)
    assert 0.92 <= rates["2027"] <= 1.0
    assert r["start_year_stats"]["electrification_rate"] == pytest.approx(
        info["start_year_electrification_rate"])
    total = r["summary_by_technology"]["Total"]
    assert total["PopulationTotal"] == pytest.approx(SCENARIO["end_year_pop"], abs=10)
    assert r["summary_by_technology"]["Non-electrified"]["Population2030"] == 0
    produced = {f["file"] for f in r["files"]}
    assert {"base_Results.csv", "base_Summaries.csv", "base_Params.json", "base_Run.json", "engine.log",
            "job.json", "params.json"} <= produced
    assert any(f.startswith("new_mv_lines_base_") for f in produced)

    assert out["columns"]["settlements"] == 4385
    # The Uganda input already carries an earlier FinalElecCode2020 calibration column.
    assert out["columns"]["per_year_metrics"]["FinalElecCode"] == [2020, 2024, 2027, 2030]

    groups = out["by_urban"]["groups"]
    assert sum(g["population"] for g in groups) == pytest.approx(total["PopulationTotal"], rel=1e-4)
    assert out["by_urban_2027"]["year"] == 2027

    c = out["compare"]
    assert set(c["parameter_differences"]) == {"pv_cost", "battery_cost", "diesel_price"}
    assert c["final_electrification_rate"]["cheap_pv"] == pytest.approx(1.0)

    assert out["cancelled"]["status"] == "cancelled"
    statuses = {run["name"]: run["status"] for run in out["runs"]["runs"]}
    assert statuses == {"base": "succeeded", "cheap_pv": "succeeded", "to_cancel": "cancelled"}
    assert "no result yet" in out["cancelled_results"]


@pytest.mark.slow
@pytest.mark.skipif(not DJIBOUTI_CSV.exists(), reason="OnSSET test data not available")
def test_calibration_end_to_end(tmp_path):
    params = {"start_year": 2024, "pop_start_year": 1_150_000, "urban_ratio_start_year": 0.78,
              "grid_elec_ratio_start_year": 0.65, "grid_urban_elec_ratio": 0.8, "grid_rural_elec_ratio": 0.2}

    async def steps(session, init):
        out = {}
        # dj-test.csv has no MGDist column: refused unless mini-grid calibration is switched off.
        out["refused"] = error_text(await session.call_tool("start_calibration", {
            "input_csv": str(DJIBOUTI_CSV), "params": params, "run_name": "dj"}))
        payload(await session.call_tool("start_calibration", {
            "input_csv": str(DJIBOUTI_CSV), "params": {**params, "mg_dist": 0}, "run_name": "dj"}))
        out["status"] = await wait_for(session, "dj", timeout=300)
        out["results"] = payload(await session.call_tool("get_run_results", {"run_name": "dj"}))
        calibrated = out["results"]["calibrated_csv"]
        out["revalidated"] = payload(await session.call_tool("validate_inputs", {
            "input_csv": calibrated, "workflow": "calibration"}))
        out["scenario_check"] = payload(await session.call_tool("validate_inputs", {
            "input_csv": calibrated, "workflow": "scenario", "pv_csv": str(UGANDA_FILES["pv_csv"]),
            "wind_csv": str(UGANDA_FILES["wind_csv"]), "mv_lines": str(UGANDA_FILES["mv_lines"]),
            "params": {"start_year": 2024}})) if HAVE_UGANDA else None
        return out

    out = run_session(env_for(tmp_path), steps)
    assert "MGDist" in out["refused"]
    assert out["status"]["status"] == "succeeded", out["status"]
    cal = out["results"]["calibration"]
    assert cal["population"] == pytest.approx(1_150_000)
    assert cal["grid_electrification_rate"] == pytest.approx(0.65, abs=0.01)
    assert cal["settlements"] == 1473
    assert out["revalidated"]["ok"]
    if out["scenario_check"] is not None:
        settlements = out["scenario_check"]["reports"][0]
        assert settlements["ok"], settlements["errors"]
        assert settlements["info"]["start_year_electrification_rate"] == pytest.approx(0.65, abs=0.01)
        # Djibouti settlements with Uganda MV lines: flagged, not silently accepted.
        assert any("do not overlap" in w for w in out["scenario_check"]["reports"][3]["warnings"])
