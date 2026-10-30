"""Result readers on a hand-made run folder shaped like the engine's outputs."""
import json

import pandas as pd
import pytest

import onsset_config as cfg
import onsset_results as results

LABELS = ["Grid_dens", "Grid_ext", "SA_PV", "MG_PV_Hybrid", "MG_Wind", "MG_Hydro", "Non-electrified", "Total"]


def fake_run(name, pv_cost=1400, invest=10.0):
    d = cfg.run_dir(name)
    d.mkdir(parents=True)
    files = {"results": str(d / f"{name}_Results.csv"), "summary": str(d / f"{name}_Summaries.csv"),
             "params": str(d / f"{name}_Params.json")}
    summary = pd.DataFrame({"Population2030": [50, 20, 30, 0, 0, 0, 0, 100],
                            "NewConnections2030": [5, 4, 6, 0, 0, 0, 0, 15],
                            "Capacity2030 (MW)": [1.0, 0.5, 0.2, 0, 0, 0, 0, 1.7],
                            "Investment2030 (million USD)": [invest, 2.0, 1.0, 0, 0, 0, 0, invest + 3],
                            "Emissions2030 (ktCO2)": [0.3, 0.1, 0, 0, 0, 0, 0, 0.4]}, index=LABELS)
    summary.to_csv(files["summary"])
    pd.DataFrame({"id": [1, 2, 3, 4], "Admin_1": ["A", "A", "B", "B"], "FinalElecCode2030": [1, 2, 3, 3],
                  "Pop2030": [50, 20, 10, 20], "NewConnections2030": [5, 4, 2, 4],
                  "NewCapacity2030": [1000, 500, 100, 100], "InvestmentCost2030": [1e7, 2e6, 4e5, 6e5],
                  "Pop2024": [40, 15, 8, 15]}).to_csv(files["results"], index=False)
    with open(files["params"], "w") as f:
        json.dump({"params": {"pv_cost": pv_cost, "end_year": 2030}}, f)
    result = {"status": "success", "scenario_name": name, "years": [2030],
              "start_year_stats": {"population": 78}, "electrification_rate": {"2030": 1.0},
              "summary": json.loads(summary.to_json(orient="index")), "files": files}
    (d / f"{name}_Run.json").write_text(json.dumps(result))


def test_summary_and_files(workspace):
    fake_run("a")
    s = results.summary("a")
    assert s["summary_by_technology"]["Total"]["Population2030"] == 100
    assert s["units"]["Investment"] == "million USD"
    assert {f["file"] for f in s["files"]} == {"a_Results.csv", "a_Summaries.csv", "a_Params.json", "a_Run.json"}


def test_result_columns(workspace):
    fake_run("a")
    c = results.result_columns("a")
    assert c["settlements"] == 4
    assert c["per_year_metrics"]["Pop"] == [2024, 2030]
    assert set(c["static_columns"]) == {"id", "Admin_1"}


def test_breakdown(workspace):
    fake_run("a")
    b = results.breakdown("a", "Admin_1")
    assert b["year"] == 2030 and b["n_groups"] == 2
    a, bgroup = b["groups"]
    assert a["group"] == "A" and a["population"] == 70 and a["investment_usd"] == 1.2e7
    assert a["population_by_technology"] == {"Grid_dens": 50.0, "Grid_ext": 20.0}
    assert bgroup["population_by_technology"] == {"SA_PV": 30.0}
    with pytest.raises(ValueError, match="Candidates"):
        results.breakdown("a", "Nope")
    with pytest.raises(ValueError, match="not a model year"):
        results.breakdown("a", "Admin_1", year=2040)


def test_compare(workspace):
    fake_run("a")
    fake_run("b", pv_cost=900, invest=8.0)
    c = results.compare(["a", "b"])
    assert c["parameter_differences"] == {"pv_cost": {"a": 1400, "b": 900}}
    assert c["by_technology"]["Investment"]["a"]["Grid_dens"] == 10.0
    assert c["by_technology"]["Investment"]["b"]["Total"] == 11.0
    assert c["final_electrification_rate"] == {"a": 1.0, "b": 1.0}
    with pytest.raises(ValueError, match="at least two"):
        results.compare(["a"])


def test_missing_and_failed_runs(workspace):
    with pytest.raises(ValueError, match="No run named"):
        results.summary("ghost")
    d = cfg.run_dir("failed")
    d.mkdir(parents=True)
    with pytest.raises(ValueError, match="no result yet"):
        results.summary("failed")
    (d / "failed_Run.json").write_text(json.dumps({"status": "error", "message": "KeyError: 'GHI'"}))
    with pytest.raises(ValueError, match="KeyError: 'GHI'"):
        results.summary("failed")


def test_deleted_output_reported(workspace):
    fake_run("a")
    (cfg.run_dir("a") / "a_Results.csv").unlink()
    with pytest.raises(ValueError, match="Settlement results CSV is missing"):
        results.result_columns("a")


def test_calibration_summary(workspace):
    d = cfg.run_dir("cal")
    d.mkdir(parents=True)
    csv = d / "OnSSET_InputFile_Calibrated.csv"
    csv.write_text("id\n1\n")
    (d / "cal_Run.json").write_text(json.dumps({
        "status": "success", "kind": "calibration", "name": "cal",
        "calibration": {"start_year": 2024, "electrification_rate": 0.65},
        "files": {"calibrated_csv": str(csv)}}))
    s = results.calibration_summary("cal")
    assert s["calibrated_csv"] == str(csv.resolve())
    assert s["calibration"]["electrification_rate"] == 0.65
    assert {f["file"] for f in s["files"]} == {"OnSSET_InputFile_Calibrated.csv", "cal_Run.json"}
    with pytest.raises(ValueError, match="not a scenario run"):
        results.summary("cal")
