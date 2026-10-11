from __future__ import annotations

import json
from pathlib import Path

from NARP import narp_mcp
from NARP.narp_mcp import REQUIRED_FILES, _JobManager, parse_output, validate_input_dir


def _input_files(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_FILES:
        (root / name).write_text("fixture\n", encoding="utf-8")


def test_required_inputs_are_complete(tmp_path):
    _input_files(tmp_path)
    result = validate_input_dir(str(tmp_path))
    assert result["valid"] is True
    assert set(result["required_files"]) == set(REQUIRED_FILES)


def test_validate_input_reports_pipeline_files(tmp_path):
    (tmp_path / "ZZTC.csv").write_text("x", encoding="utf-8")
    result = validate_input_dir(str(tmp_path))
    assert result["valid"] is False
    assert {"ZZFC.csv", "ZZOD.csv", "ZZDD.csv", "LEEI"} <= set(result["missing"])


def test_leei_must_be_a_file(tmp_path):
    _input_files(tmp_path)
    (tmp_path / "LEEI").unlink()
    (tmp_path / "LEEI").mkdir()
    result = validate_input_dir(str(tmp_path))
    assert result["valid"] is False
    assert "LEEI" in result["missing"]


def test_parser_matches_narp_table12_pool_and_table13_layouts(tmp_path):
    path = tmp_path / "output.txt"
    path.write_text(
        """
TABLE 12
  1  AV       1.00   2.00   3.00   4.00   5.00  GC
  2  AV       6.00   7.00   8.00   9.00  10.00  TC
  3  AV      11.00  12.00  13.00  14.00  15.00  GT
POOL STATISTICS
  AV          16.00  17.00  18.00  19.00  20.00  GC
  AV          21.00  22.00  23.00  24.00  25.00  TC
  AV          26.00  27.00  28.00  29.00  30.00  GT
TABLE 13
  A1          100  120  20  1.5  4.0  5.0  2.5  6.0  3.5
  CUSTOM_AREA 200  250  25  2.0  7.0  8.0  4.0  9.0  5.0
  ERCOT       300  400  10  3.0  9.0 10.0  5.0 12.0  6.0
""",
        encoding="utf-8",
    )
    result = parse_output(str(path))

    assert len(result["table_12"]) == 3
    assert [row["remark"] for row in result["table_12"]] == ["GC", "TC", "GT"]
    assert len(result["pool"]) == 3
    assert result["pool"][0]["label"] == "AV"
    assert result["pool"][2]["LOLE"] == 29.0
    assert result["summary"]["A1"]["HLOLE"] == 1.5
    assert result["summary"]["A1"]["HLOLE_pct_sd"] == 4.0
    assert result["summary"]["A1"]["EUE"] == 5.0
    assert result["summary"]["A1"]["EUE_pct_sd"] == 2.5
    assert result["summary"]["A1"]["LOLE"] == 6.0
    assert result["summary"]["A1"]["LOLE_pct_sd"] == 3.5
    assert result["summary"]["CUSTOM_AREA"]["LOLE"] == 9.0
    assert result["summary"]["ERCOT"]["LOLE_pct_sd"] == 6.0


def test_table13_24_step_layout_maps_five_columns_to_lole(tmp_path):
    path = tmp_path / "output.txt"
    path.write_text(
        """
TABLE 13
  REGION_X  100  120  20  1.5  4.0
""",
        encoding="utf-8",
    )
    result = parse_output(str(path))
    assert result["summary"]["REGION_X"] == {
        "label": "REGION_X",
        "peak": 100.0,
        "installed": 120.0,
        "PCT_RES": 20.0,
        "LOLE": 1.5,
        "LOLE_pct_sd": 4.0,
    }


def test_child_invokes_narp_entry_point_in_subprocess():
    assert "from reliabilityassessment.monte_carlo.narpMain import narpMain" in narp_mcp._CHILD_CODE
    assert "narpMain(sys.argv[1])" in narp_mcp._CHILD_CODE


def test_jobs_index_is_loaded_on_read_paths(tmp_path, monkeypatch):
    index = tmp_path / "jobs_index.json"
    job = {
        "id": "job_existing",
        "status": "completed",
        "created_at": 1.0,
        "job_dir": str(tmp_path / "job_existing"),
        "output_path": str(tmp_path / "job_existing" / "output.txt"),
        "log_path": str(tmp_path / "job_existing" / "run.log"),
        "error": None,
    }
    index.write_text(json.dumps({"job_existing": job}), encoding="utf-8")
    monkeypatch.setattr(narp_mcp, "_job_root", lambda: tmp_path)
    manager = _JobManager()

    assert manager.get_job("job_existing")["job"]["status"] == "completed"
    assert manager.list_jobs()["jobs"][0]["id"] == "job_existing"


def test_cancelled_pending_job_never_launches(tmp_path, monkeypatch):
    manager = _JobManager()
    manager._index_path = tmp_path / "jobs_index.json"
    job_dir = tmp_path / "job_pending"
    job_dir.mkdir()
    (job_dir / "input").mkdir()
    job = {
        "id": "job_pending",
        "status": "cancelled",
        "job_dir": str(job_dir),
        "created_at": 1.0,
        "started_at": None,
        "finished_at": 2.0,
        "output_path": str(job_dir / "output.txt"),
        "log_path": str(job_dir / "run.log"),
        "error": None,
    }
    manager._jobs[job["id"]] = job
    manager._index_path.write_text(json.dumps(manager._jobs), encoding="utf-8")

    def unexpected_popen(*args, **kwargs):
        raise AssertionError("cancelled pending job must not spawn a child")

    monkeypatch.setattr(narp_mcp.subprocess, "Popen", unexpected_popen)
    manager._run("job_pending")
    assert manager._jobs["job_pending"]["status"] == "cancelled"


def test_cancel_during_process_start_terminates_child(tmp_path, monkeypatch):
    manager = _JobManager()
    manager._index_path = tmp_path / "jobs_index.json"
    job_dir = tmp_path / "job_race"
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True)
    job = {
        "id": "job_race",
        "status": "pending",
        "job_dir": str(job_dir),
        "created_at": 1.0,
        "started_at": None,
        "finished_at": None,
        "output_path": str(job_dir / "output.txt"),
        "log_path": str(job_dir / "run.log"),
        "error": None,
    }
    manager._jobs[job["id"]] = job
    manager._index_path.write_text(json.dumps(manager._jobs), encoding="utf-8")

    class FakeProcess:
        terminated = False

        def __init__(self):
            self.returncode = -15

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return None if not self.terminated else self.returncode

        def kill(self):
            self.terminated = True

    process = FakeProcess()

    def fake_popen(*args, **kwargs):
        # Reproduce cancellation after Popen begins but before it is registered.
        manager.cancel("job_race")
        return process

    monkeypatch.setattr(narp_mcp.subprocess, "Popen", fake_popen)
    manager._run("job_race")
    assert process.terminated
    assert manager._jobs["job_race"]["status"] == "cancelled"


def test_nonempty_params_are_rejected(tmp_path):
    _input_files(tmp_path)
    manager = _JobManager()
    result = manager.create_job(str(tmp_path), {"unsupported": True})
    assert result["success"] is False
    assert "params are not supported" in result["error"]
