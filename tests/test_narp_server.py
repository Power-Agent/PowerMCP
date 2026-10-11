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


def test_parser_matches_upstream_narp_output_excerpt(tmp_path):
    # Excerpted from Breakthrough-Energy/reliability-assessment's MIT-licensed
    # reliabilityassessment/integration_test/output_python.txt.
    path = tmp_path / "output.txt"
    path.write_text(
        """
TABLE 12

             FINAL RESULTS AFTER 3549 REPLICATIONS

  AREA FORECAST    HOURLY STATISTICS            PEAK STATISTICS           REMARKS
  NO   NO        HLOLE    XLOL       EUE       LOLE      XLOL
                (HRS/YR)  (MW)      (MWH)     (DAYS/YR)  (MW)
   1  AV        0.09    130.54        11        0.03    134.15            GC
   1  AV        0.34    109.04        37        0.07    120.08            TC
   1  AV        0.43    113.42        49        0.10    124.41            GT

   2  AV        0.08    100.55         8        0.02    115.48            GC
   2  AV        0.00      0.00         0        0.00      0.00            TC
   2  AV        0.08    100.55         8        0.02    115.48            GT

   3  AV        0.08    121.87        10        0.03    118.08            GC
   3  AV        0.41    110.53        45        0.08    113.27            TC
   3  AV        0.49    112.42        55        0.11    114.46            GT

   4  AV        0.10    127.34        12        0.03    125.80            GC
   4  AV        0.35    107.82        38        0.07    128.25            TC
   4  AV        0.44    112.04        50        0.10    127.52            GT

   5  AV        0.09    123.54        11        0.03    113.22            GC
   5  AV        0.31    101.56        32        0.06    121.36            TC
   5  AV        0.40    106.57        43        0.09    118.72            GT

           POOL STATISTICS

      AV       0.001    252.00         0       0.000    195.00            GC
      AV       0.000      1.00         0       0.000      0.00            TC
      AV       0.001    168.33         0       0.000    195.00            GT

TABLE   13

          AREA       PEAK        INSTALLED   AREA           HLOLE                   EUE                LOLE
                                                       ----------------        ----------------     ----------------
                                 CAPACITY    PCT RES   MAGN      PCT SD        MAGN      PCT SD     MAGN      PCT SD
          A1          3000         3405      13.5       0.430      2.499          49          4     0.102     5.229
          A2          3000         3405      13.5       0.078      5.891           8          9     0.023    10.915
          A3          3000         3405      13.5       0.491      2.406          55          3     0.113     4.981
          A4          3000         3405      13.5       0.444      2.537          50          4     0.101     5.270
          A5          3000         3405      13.5       0.402      2.584          43          4     0.093     5.449

          ERCOT      15000        17025      13.5       0.001    3858.468           0       3723     0.000   3889.730

TABLE 14
""",
        encoding="utf-8",
    )
    result = parse_output(str(path))

    assert len(result["table_12"]) == 15
    assert [row["remark"] for row in result["table_12"][:3]] == ["GC", "TC", "GT"]
    assert len(result["pool"]) == 3
    assert [row["remark"] for row in result["pool"]] == ["GC", "TC", "GT"]
    assert result["pool"][0]["HLOLE"] == 0.001
    assert result["summary"]["A1"]["HLOLE"] == 0.430
    assert result["summary"]["A1"]["HLOLE_pct_sd"] == 2.499
    assert result["summary"]["A1"]["EUE"] == 49.0
    assert result["summary"]["A1"]["EUE_pct_sd"] == 4.0
    assert result["summary"]["A1"]["LOLE"] == 0.102
    assert result["summary"]["A1"]["LOLE_pct_sd"] == 5.229
    assert set(result["summary"]) == {"A1", "A2", "A3", "A4", "A5", "ERCOT"}


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
