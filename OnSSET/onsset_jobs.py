"""Background OnSSET runs, one subprocess per run.

A run lives in ``<workspace>/<name>/``:

    job.json        what was started on which inputs, when, and how it ended (written by this module)
    params.json     the validated parameters handed to the engine
    engine.log      stdout + stderr of the engine (OnSSET prints its progress there)
    <name>_Run.json result written by the engine or calibration CLI when it finishes
    ...             model outputs

The subprocess never shares the server's stdin/stdout, which carry the MCP protocol. Status is
derived from the files, so runs started by an earlier server process can still be inspected.
"""

import atexit
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import onsset_config as cfg

JOB_FILE = "job.json"
LOG_FILE = "engine.log"
PARAMS_FILE = "params.json"

_lock = threading.Lock()
_procs = {}  # name -> Popen started by this server process


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(path, data):
    tmp = Path(path).with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def result_path(directory, name):
    return Path(directory) / f"{name}_Run.json"


def _pid_alive(pid):
    if not pid:
        return False
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _running_names():
    return [n for n, p in _procs.items() if p.poll() is None]


def params_path(name):
    return cfg.run_dir(name) / PARAMS_FILE


def start(kind, name, script, args, params, inputs, overwrite=False):
    """Start ``python script args`` for run ``name`` after writing ``params`` to ``params_path(name)``.

    Raises ValueError when it cannot start.
    """
    directory = cfg.run_dir(name)
    with _lock:
        running = _running_names()
        if name in running:
            raise ValueError(f"Run '{name}' is already running.")
        if len(running) >= cfg.max_concurrent_runs():
            raise ValueError(f"{len(running)} run(s) already in progress ({', '.join(running)}); the limit is "
                             f"{cfg.max_concurrent_runs()} (ONSSET_MAX_CONCURRENT_RUNS). Wait or cancel one.")
        if directory.exists() and any(directory.iterdir()):
            job = _read_json(directory / JOB_FILE) or {}
            if job.get("status") == "running" and _pid_alive(job.get("pid")):
                raise ValueError(f"Run '{name}' is still running in another server process (pid {job['pid']}).")
            if not overwrite:
                raise ValueError(f"Run '{name}' already exists in {directory}. Choose another name or pass "
                                 "overwrite=true to delete its previous outputs.")
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)
        _write_json(directory / PARAMS_FILE, params)

        cmd = [cfg.engine_python(), "-u", str(script), *args, "--result-json", str(result_path(directory, name))]
        log = open(directory / LOG_FILE, "w", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"}
        try:
            proc = subprocess.Popen(cmd, cwd=str(cfg.HERE), stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, creationflags=flags, env=env)
        except OSError as e:
            log.close()
            raise ValueError(f"Could not start the engine with {cmd[0]}: {e}") from e
        log.close()  # the child holds its own handle
        _procs[name] = proc
        job = {"name": name, "kind": kind, "status": "running", "pid": proc.pid, "started": _now(),
               "finished": None, "returncode": None, "inputs": inputs, "command": cmd,
               "directory": str(directory)}
        _write_json(directory / JOB_FILE, job)
    threading.Thread(target=_watch, args=(name, proc, directory), daemon=True).start()
    return job


def _watch(name, proc, directory):
    code = proc.wait()
    with _lock:
        job = _read_json(directory / JOB_FILE) or {}
        if job.get("status") == "running":
            result = _read_json(result_path(directory, name)) or {}
            job["status"] = "succeeded" if code == 0 and result.get("status") == "success" else "failed"
        job.update(returncode=code, finished=job.get("finished") or _now())
        _write_json(directory / JOB_FILE, job)


def tail(path, lines):
    """Last ``lines`` lines of a text file, read from the end so large logs stay cheap."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 64 * 1024 * max(1, lines // 50 + 1)))
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    return text.splitlines()[-lines:]


def status(name, log_lines=20):
    directory = cfg.run_dir(name)
    job = _read_json(directory / JOB_FILE)
    result = _read_json(result_path(directory, name))
    if job is None and result is None:
        raise ValueError(f"No run named '{name}' in {cfg.workspace()}.")
    job = dict(job or {"name": name, "kind": "unknown", "status": "finished-externally"})
    proc = _procs.get(name)
    if job.get("status") == "running":
        alive = proc.poll() is None if proc else _pid_alive(job.get("pid"))
        if not alive:
            # The watcher thread may not have written the final state yet, or the server that started
            # the run died with it. The result file decides.
            if result is not None:
                job["status"] = "succeeded" if result.get("status") == "success" else "failed"
            else:
                job["status"] = "interrupted"
    if job["status"] == "running" and job.get("started"):
        started = datetime.fromisoformat(job["started"])
        job["elapsed_s"] = round((datetime.now(timezone.utc) - started).total_seconds())
    job["log_tail"] = tail(directory / LOG_FILE, log_lines) if log_lines else []
    if result is not None and job["status"] != "running":
        job["result_status"] = result.get("status")
        if result.get("status") != "success":
            job["error"] = result.get("message")
    elif job["status"] in ("failed", "interrupted"):
        job["error"] = "The engine stopped without writing a result; see log_tail."
    return job


def cancel(name):
    with _lock:
        proc = _procs.get(name)
        directory = cfg.run_dir(name)
        job = _read_json(directory / JOB_FILE)
        if job is None:
            raise ValueError(f"No run named '{name}' in {cfg.workspace()}.")
        if proc is None or proc.poll() is not None:
            raise ValueError(f"Run '{name}' is not running in this server process (status: {job.get('status')}).")
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=20)
        job.update(status="cancelled", finished=_now(), returncode=proc.returncode)
        _write_json(directory / JOB_FILE, job)
    return job


def list_runs():
    runs = []
    for directory in sorted(p for p in cfg.workspace().iterdir() if p.is_dir()):
        if not cfg.RUN_NAME_RE.match(directory.name):
            continue
        if not (directory / JOB_FILE).exists() and not result_path(directory, directory.name).exists():
            continue
        s = status(directory.name, log_lines=0)
        runs.append({k: s.get(k) for k in ("name", "kind", "status", "started", "finished", "error")})
    return runs


@atexit.register
def _stop_children():
    """Do not leave engines running once the client that asked for them is gone."""
    for name, proc in list(_procs.items()):
        if proc.poll() is None:
            proc.terminate()
            directory = cfg.run_dir(name)
            job = _read_json(directory / JOB_FILE) or {}
            job.update(status="cancelled", finished=_now(), error="MCP server exited during the run")
            try:
                _write_json(directory / JOB_FILE, job)
            except OSError:
                pass
