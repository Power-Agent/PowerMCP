"""Job manager lifecycle with a stand-in engine script (no OnSSET needed)."""
import json
import time

import pytest

import onsset_config as cfg
import onsset_jobs as jobs

FAKE_ENGINE = """
import argparse, json, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("--mode"); ap.add_argument("--params"); ap.add_argument("--result-json")
a = ap.parse_args()
print("engine says hello")  # OnSSET prints to stdout; it must land in engine.log
params = json.load(open(a.params))
if a.mode == "sleep":
    time.sleep(60)
if a.mode == "crash":
    sys.exit(3)
status = "success" if a.mode == "ok" else "error"
json.dump({"status": status, "message": "boom", "echo": params}, open(a.result_json, "w"))
sys.exit(0 if status == "success" else 1)
"""


@pytest.fixture
def engine(workspace, tmp_path):
    script = tmp_path / "fake_engine.py"
    script.write_text(FAKE_ENGINE)
    return script


def start(engine, name, mode, **kw):
    return jobs.start("scenario", name, engine, ["--mode", mode, "--params", str(jobs.params_path(name))],
                      {"x": 1}, {"input_csv": "in.csv"}, **kw)


def wait(name, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = jobs.status(name)
        if s["status"] != "running":
            return s
        time.sleep(0.2)
    raise AssertionError(f"{name} still running")


def test_successful_run(engine):
    job = start(engine, "ok1", "ok")
    assert job["status"] == "running" and job["inputs"] == {"input_csv": "in.csv"}
    s = wait("ok1")
    assert s["status"] == "succeeded" and s["result_status"] == "success"
    assert "engine says hello" in s["log_tail"]
    result = json.loads((cfg.run_dir("ok1") / "ok1_Run.json").read_text())
    assert result["echo"] == {"x": 1}
    assert [r["name"] for r in jobs.list_runs()] == ["ok1"]


def test_engine_error_and_crash(engine):
    start(engine, "err1", "error")
    s = wait("err1")
    assert s["status"] == "failed" and s["error"] == "boom"
    start(engine, "crash1", "crash")
    s = wait("crash1")
    assert s["status"] == "failed" and "without writing a result" in s["error"]


def test_existing_run_needs_overwrite(engine):
    start(engine, "dup", "ok")
    wait("dup")
    with pytest.raises(ValueError, match="overwrite=true"):
        start(engine, "dup", "ok")
    start(engine, "dup", "ok", overwrite=True)
    assert wait("dup")["status"] == "succeeded"


def test_concurrency_limit_and_cancel(engine):
    start(engine, "slow", "sleep")
    with pytest.raises(ValueError, match="already in progress"):
        start(engine, "other", "ok")
    with pytest.raises(ValueError, match="already running"):
        start(engine, "slow", "ok", overwrite=True)
    job = jobs.cancel("slow")
    assert job["status"] == "cancelled"
    assert jobs.status("slow")["status"] == "cancelled"
    with pytest.raises(ValueError, match="not running"):
        jobs.cancel("slow")


def test_status_survives_server_restart(engine):
    start(engine, "persist", "ok")
    wait("persist")
    jobs._procs.clear()  # as if a new server process started
    assert jobs.status("persist")["status"] == "succeeded"
    # A run whose process vanished without a result is reported as interrupted.
    job_file = cfg.run_dir("persist") / jobs.JOB_FILE
    job = json.loads(job_file.read_text())
    job.update(status="running", pid=999999)
    job_file.write_text(json.dumps(job))
    (cfg.run_dir("persist") / "persist_Run.json").unlink()
    assert jobs.status("persist")["status"] == "interrupted"


def test_unknown_run_and_bad_names(workspace):
    with pytest.raises(ValueError, match="No run named"):
        jobs.status("nothing")
    for bad in ("../escape", "a/b", "", ".hidden", "x" * 65):
        with pytest.raises(ValueError, match="Invalid run name"):
            cfg.run_dir(bad)


def test_tail_reads_only_the_end(tmp_path):
    log = tmp_path / "l.log"
    log.write_text("\n".join(f"line {i}" for i in range(100000)))
    assert jobs.tail(log, 3) == ["line 99997", "line 99998", "line 99999"]
    assert jobs.tail(tmp_path / "missing.log", 3) == []
