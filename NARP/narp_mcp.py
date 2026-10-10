"""MCP connector for the external Breakthrough Energy NARP reliability package.

The NARP implementation is intentionally not vendored. Install the upstream
package separately from:
https://github.com/Breakthrough-Energy/reliability-assessment

The connector launches narpMain(TEST_DIR) in an isolated Python process so the
MCP stdio process stays responsive and a running job can be terminated.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from threading import RLock
from typing import Any

from mcp.server.mcpserver import MCPServer

_repo_root = str(Path(__file__).resolve().parent.parent)
_repo_added = _repo_root not in sys.path
if _repo_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import PathNotAllowed, checked_path, checked_read_tree, ensure_checked_directory
    from powermcp.paths import runs_dir
finally:
    if _repo_added:
        sys.path.remove(_repo_root)

logger = logging.getLogger(__name__)
mcp = MCPServer("NARP Reliability Assessment")

REQUIRED_FILES = (
    "ZZMC.csv", "ZZUD.csv", "ZZLD.csv", "ZZTD.csv", "ZZTC.csv",
    "ZZFC.csv", "ZZOD.csv", "ZZDD.csv", "LEEI",
)

_CHILD_CODE = (
    "import sys\n"
    "from reliabilityassessment.monte_carlo.narpMain import narpMain\n"
    "narpMain(sys.argv[1])\n"
)


def _now() -> float:
    return time.time()


def _job_root() -> Path:
    return Path(ensure_checked_directory(
        str(runs_dir("narp", create=False)),
        purpose="NARP generated job root",
    ))


def _safe_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def validate_input_dir(input_dir: str) -> dict[str, Any]:
    try:
        root = Path(checked_read_tree(input_dir, purpose="NARP input directory"))
    except PathNotAllowed as exc:
        return {"valid": False, "error": str(exc)}

    missing: list[str] = []
    for name in REQUIRED_FILES:
        p = root / name
        if not p.exists():
            missing.append(name)
        elif name != "LEEI" and not p.is_file():
            missing.append(name)
        elif name == "LEEI" and not (p.is_file() or p.is_dir()):
            missing.append(name)

    return {
        "valid": not missing,
        "input_dir": str(root),
        "required_files": list(REQUIRED_FILES),
        "missing": missing,
    }


def _read_output(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_output(output_file: str) -> dict[str, Any]:
    """Parse NARP TABLE 12, TABLE 13, and pool statistics."""
    path = Path(output_file)
    result: dict[str, Any] = {"table_12": [], "summary": {}, "pool": []}
    try:
        text = _read_output(path)
    except OSError:
        return result

    table_matches = list(re.finditer(r"(?im)^\s*TABLE\s+([0-9]+)\s*$", text))
    sections: dict[int, str] = {}
    for i, match in enumerate(table_matches):
        number = int(match.group(1))
        end = table_matches[i + 1].start() if i + 1 < len(table_matches) else len(text)
        sections[number] = text[match.end():end]

    block12 = sections.get(12, "")
    pool_marker = re.search(r"(?im)^\\s*POOL\\s+STATISTICS\\s*$", block12)
    if pool_marker:
        area_block = block12[:pool_marker.start()]
        pool_block = block12[pool_marker.end():]
    else:
        area_block, pool_block = block12, ""

    number_pattern = re.compile(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[Ee][-+]?\\d+)?")

    def metrics(values: list[str]) -> dict[str, float | None]:
        nums = [float(value) for value in values[:5]]
        if len(nums) < 4:
            return {}
        return {
            "HLOLE": nums[0],
            "XLOL_hourly": nums[1],
            "EUE": nums[2],
            "LOLE": nums[3],
            "XLOL_peak": nums[4] if len(nums) > 4 else None,
        }

    for line in area_block.splitlines():
        tokens = line.split()
        if len(tokens) < 6 or not tokens[0].isdigit():
            continue
        # Actual NARP reports put the forecast code (usually AV) before the
        # five metrics and the GC/TC/GT remark after them.
        actual_row = (
            len(tokens) >= 8
            and all(number_pattern.fullmatch(value) for value in tokens[2:7])
            and tokens[-1].isalpha()
        )
        if actual_row:
            area = int(tokens[0])
            forecast = tokens[1]
            values = tokens[2:7]
            remark = tokens[-1]
        else:
            # Retain compatibility with compact/legacy rows where the second
            # column itself contains the remark.
            area = int(tokens[0])
            forecast = None
            remark = tokens[1]
            values = tokens[2:]
            if not all(number_pattern.fullmatch(value) for value in values):
                continue
        parsed = metrics(values)
        if not parsed:
            continue
        result["table_12"].append({
            "area": area,
            "forecast": forecast,
            "remark": remark,
            **parsed,
        })

    # POOL STATISTICS uses unnumbered AV rows and the same metric columns.
    for line in pool_block.splitlines():
        tokens = line.split()
        if (
            len(tokens) < 7
            or tokens[0].upper() != "AV"
            or not tokens[-1].isalpha()
            or not all(number_pattern.fullmatch(value) for value in tokens[1:-1])
        ):
            continue
        parsed = metrics(tokens[1:-1])
        if parsed:
            result["pool"].append({
                "label": "AV",
                "remark": tokens[-1],
                **parsed,
            })

    block13 = sections.get(13, "")
    for line in block13.splitlines():
        s = line.strip()
        m = re.match(r"^(A\\d+|AV|ERCOT)\\s+(.*)$", s, flags=re.I)
        if not m:
            continue
        values = re.findall(r"[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[Ee][-+]?\\d+)?", m.group(2))
        if len(values) < 4:
            continue
        nums = [float(v) for v in values]
        entry: dict[str, Any] = {"label": m.group(1).upper()}
        fields = (
            ("peak", 0), ("installed", 1), ("PCT_RES", 2),
            ("HLOLE", 3), ("HLOLE_pct_sd", 4),
            ("EUE", 5), ("EUE_pct_sd", 6),
            ("LOLE", 7), ("LOLE_pct_sd", 8),
        )
        for name, index in fields:
            if index < len(nums):
                entry[name] = nums[index]
        result["summary"][entry["label"]] = entry

    result["areas"] = result["table_12"]
    return result


class _JobManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._procs: dict[str, subprocess.Popen[bytes]] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._index_path: Path | None = None

    def _ensure_storage(self) -> Path:
        if self._index_path is None:
            root = _job_root()
            self._index_path = root / "jobs_index.json"
            self._load_index()
        return self._index_path

    def _load_index(self) -> None:
        index_path = self._index_path
        if index_path is None or not index_path.exists():
            return
        try:
            persisted = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            persisted = {}
        if not isinstance(persisted, dict):
            return
        for job_id, job in persisted.items():
            if not isinstance(job, dict):
                continue
            job = dict(job)
            if job.get("status") in {"pending", "running"}:
                job["status"] = "failed"
                job["error"] = "NARP MCP server restarted before the job completed."
                job["finished_at"] = _now()
            self._jobs[str(job_id)] = job

    def _persist(self) -> None:
        _atomic_json_write(self._ensure_storage(), self._jobs)

    def _write_metadata(self, job: dict[str, Any]) -> None:
        _atomic_json_write(Path(job["job_dir"]) / "metadata.json", job)

    def _update(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(changes)
            self._write_metadata(job)
            self._persist()

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            work_dir = Path(job["job_dir"])
            input_dir = work_dir / "input"
            log_path = work_dir / "run.log"
            job["status"] = "running"
            job["started_at"] = _now()
            self._write_metadata(job)
            self._persist()

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        try:
            with log_path.open("wb") as log:
                proc = subprocess.Popen(
                    [sys.executable, "-c", _CHILD_CODE, str(input_dir)],
                    cwd=work_dir,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
            with self._lock:
                self._procs[job_id] = proc
            returncode = proc.wait()
        except Exception as exc:
            self._update(job_id, status="failed", error=str(exc), finished_at=_now())
            return

        with self._lock:
            self._procs.pop(job_id, None)
            job = self._jobs.get(job_id)
            if not job:
                return
            if job["status"] == "cancelled":
                job["finished_at"] = job.get("finished_at") or _now()
                self._write_metadata(job)
                self._persist()
            elif returncode == 0:
                output_path = work_dir / "output.txt"
                if not output_path.exists():
                    self._update(
                        job_id,
                        status="failed",
                        error="narpMain exited successfully but did not produce output.txt.",
                        finished_at=_now(),
                    )
                    return
                self._update(
                    job_id,
                    status="completed",
                    output_path=str(output_path),
                    log_path=str(log_path),
                    finished_at=_now(),
                )
            else:
                self._update(
                    job_id,
                    status="failed",
                    error=f"narpMain failed with exit code {returncode}; see {log_path}",
                    log_path=str(log_path),
                    finished_at=_now(),
                )

    def create_job(self, input_dir: str, params: dict[str, Any]) -> dict[str, Any]:
        validation = validate_input_dir(input_dir)
        if not validation["valid"]:
            return {"success": False, **validation}

        src = Path(validation["input_dir"])
        job_id = _safe_job_id()
        job_dir = _job_root() / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        shutil.copytree(src, job_dir / "input")
        job = {
            "id": job_id,
            "status": "pending",
            "params": params,
            "job_dir": str(job_dir),
            "input_dir": str(src),
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "output_path": str(job_dir / "output.txt"),
            "log_path": str(job_dir / "run.log"),
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._write_metadata(job)
            self._persist()
        return {
            "success": True,
            "job_id": job_id,
            "job_dir": str(job_dir),
            "output_path": job["output_path"],
            "log_path": job["log_path"],
        }

    def submit(self, input_dir: str, params: dict[str, Any]) -> dict[str, Any]:
        created = self.create_job(input_dir, params)
        if not created.get("success"):
            return created
        job_id = str(created["job_id"])
        import threading
        threading.Thread(target=self._run, args=(job_id,), daemon=True).start()
        return created

    def run_sync(self, input_dir: str, params: dict[str, Any]) -> dict[str, Any]:
        created = self.create_job(input_dir, params)
        if not created.get("success"):
            return created
        self._run(str(created["job_id"]))
        return self.get_job(str(created["job_id"]))

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {"success": False, "error": f"Job not found: {job_id}"}
            return {"success": True, "job": dict(job)}

    def get_result(self, job_id: str) -> dict[str, Any]:
        state = self.get_job(job_id)
        if not state.get("success"):
            return state
        job = state["job"]
        output = Path(job["output_path"])
        if not output.exists():
            return {"success": False, "job_id": job_id, "status": "no_output", "output_path": str(output)}
        return {"success": True, "job_id": job_id, "output_path": str(output), "output": _read_output(output)}

    def get_summary(self, job_id: str) -> dict[str, Any]:
        state = self.get_job(job_id)
        if not state.get("success"):
            return state
        job = state["job"]
        output = Path(job["output_path"])
        if not output.exists():
            return {"success": False, "job_id": job_id, "status": "no_output"}
        return {"success": True, "job_id": job_id, "summary": parse_output(str(output))}

    def list_jobs(self, limit: int = 100) -> dict[str, Any]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item.get("created_at", 0), reverse=True)
        return {"success": True, "jobs": [dict(j) for j in jobs[:max(0, int(limit))]]}

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {"success": False, "error": f"Job not found: {job_id}"}
            if job["status"] not in {"pending", "running"}:
                return {"success": True, "cancelled": False, "status": job["status"]}
            proc = self._procs.get(job_id)
            job["status"] = "cancelled"
            job["finished_at"] = _now()
            self._write_metadata(job)
            self._persist()
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            except OSError:
                pass
        return {"success": True, "cancelled": True}


_jobs = _JobManager()


@mcp.tool()
def ping() -> dict[str, Any]:
    """Return connector availability without importing NARP."""
    return {"success": True, "engine": "NARP", "status": "ready", "upstream": "external"}


@mcp.tool()
def validate_input(input_dir: str) -> dict[str, Any]:
    """Validate all files actually read by NARP's input pipeline."""
    return validate_input_dir(input_dir)


@mcp.tool()
def submit_simulation(input_dir: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Submit a cancellable asynchronous NARP Monte Carlo reliability job."""
    return _jobs.submit(input_dir, dict(params or {}))


@mcp.tool()
def run_simulation_sync(input_dir: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run NARP synchronously by importing and calling narpMain(TEST_DIR)."""
    return _jobs.run_sync(input_dir, dict(params or {}))


@mcp.tool()
def get_job_status(job_id: str) -> dict[str, Any]:
    """Return durable job state, including jobs loaded after an MCP restart."""
    state = _jobs.get_job(job_id)
    if not state.get("success"):
        return state
    job = state["job"]
    return {
        "success": True,
        "job_id": job["id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "error": job["error"],
        "job_dir": job["job_dir"],
        "output_path": job["output_path"],
        "log_path": job["log_path"],
    }


@mcp.tool()
def get_job_result(job_id: str) -> dict[str, Any]:
    """Return raw output.txt for a completed NARP job."""
    return _jobs.get_result(job_id)


@mcp.tool()
def get_job_summary(job_id: str) -> dict[str, Any]:
    """Return structured TABLE 12, TABLE 13, and pool reliability results."""
    return _jobs.get_summary(job_id)


@mcp.tool()
def list_jobs(limit: int = 100) -> dict[str, Any]:
    """List persisted jobs newest first."""
    return _jobs.list_jobs(limit)


@mcp.tool()
def cancel_job(job_id: str) -> dict[str, Any]:
    """Terminate the child process for a running NARP job."""
    return _jobs.cancel(job_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
