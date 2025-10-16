import os
import shutil
import json
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
from typing import Optional
import logging

from .worker import worker_run, parse_output

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self, db_path: str = "mcp_jobs.sqlite", work_root: Optional[str] = None, max_workers: int = 1):
        # db_path parameter kept for compatibility but not used in the in-memory implementation
        self.db_path = db_path

        # Ensure work_root is located inside the project directory so results are always
        # written to the repository's mcp_jobs folder regardless of where JobManager is instantiated.
        # Project root is the parent of the package directory (two levels up from this file).
        project_root = Path(__file__).resolve().parents[1]
        if work_root:
            wr = Path(work_root)
            # If user passed a relative path, resolve it relative to project root
            if not wr.is_absolute():
                wr = project_root / wr
            self.work_root = wr.resolve()
        else:
            # default to the project's mcp_jobs folder
            self.work_root = (project_root / "mcp_jobs").resolve()

        # create the work_root directory if it doesn't exist
        self.work_root.mkdir(parents=True, exist_ok=True)

        # maintain an index file so users can quickly locate job folders
        self.index_file = self.work_root / "jobs_index.json"
        self._index = {}
        if self.index_file.exists():
            try:
                self._index = json.loads(self.index_file.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}

        # in-memory job store
        self._jobs = {}  # job_id -> job dict
        self._lock = threading.Lock()

        # use threads so worker can update in-memory state via callback
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures = {}

    def _write_index(self):
        try:
            self.index_file.write_text(json.dumps(self._index, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _write_metadata(self, job: dict):
        """Persist a job's metadata into its job_dir/metadata.json (best-effort)."""
        try:
            jd = job.get("job_dir")
            if not jd:
                return
            p = Path(jd)
            p.mkdir(parents=True, exist_ok=True)
            meta_file = p / "metadata.json"
            # prepare a serializable copy
            to_write = {
                k: job.get(k) for k in [
                    "id", "status", "params", "job_dir", "created_at", "started_at", "finished_at", "result", "error"
                ]
            }
            meta_file.write_text(json.dumps(to_write, indent=2), encoding="utf-8")
        except Exception:
            # metadata persistence is best-effort; don't raise
            pass

    def _insert_job(self, job_id: str, params: dict, job_dir: str):
        # ensure job_dir is absolute
        job_dir = str(Path(job_dir).resolve())
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "pending",
                "params": params,
                "job_dir": job_dir,
                "created_at": time.time(),
                "started_at": None,
                "finished_at": None,
                "result": None,
                "error": None,
            }
            # persist initial metadata
            self._write_metadata(self._jobs[job_id])
            # update index for quick lookup
            self._index[job_id] = job_dir
            self._write_index()
        logger.info(f"Created job {job_id} at {job_dir}")

    def _update_job(self, job_id: str, **fields):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                job[k] = v
            # persist after update
            self._write_metadata(job)

    def submit_simulation(self, test_dir: str, params: Optional[dict] = None) -> dict:
        """Submit an async job. Returns a dict with job_id and absolute paths for job_dir, output and log."""
        params = params or {}
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job_dir_path = self.work_root / job_id
        job_dir = str(job_dir_path.resolve())
        # copy inputs into job folder (create target)
        shutil.copytree(test_dir, job_dir)
        self._insert_job(job_id, params, job_dir)
        # submit to thread pool and provide update callback
        future = self.executor.submit(worker_run, job_id, job_dir, params, self._update_job)
        self._futures[job_id] = future
        # provide absolute paths for output and log files so callers can locate them immediately
        output_path = str(Path(job_dir) / "output_python.txt")
        log_path = str(Path(job_dir) / "run.log")
        return {
            "job_id": job_id,
            "job_dir": job_dir,
            "output_path": output_path,
            "log_path": log_path,
        }

    def run_simulation_sync(self, test_dir: str, params: Optional[dict] = None) -> dict:
        params = params or {}
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job_dir_path = self.work_root / job_id
        job_dir = str(job_dir_path.resolve())
        shutil.copytree(test_dir, job_dir)
        self._insert_job(job_id, params, job_dir)
        # run directly (in current thread)
        try:
            worker_run(job_id, job_dir, params, self._update_job)
            with self._lock:
                job = self._jobs.get(job_id)
                return job.copy() if job else {"job_id": job_id, "status": "completed", "result": None}
        except Exception as e:
            # persist failure
            self._update_job(job_id, status="failed", error=str(e), finished_at=time.time())
            return {"job_id": job_id, "status": "failed", "error": str(e)}

    def get_job_status(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            return {
                "job_id": job["id"],
                "status": job["status"],
                "created_at": job["created_at"],
                "started_at": job["started_at"],
                "finished_at": job["finished_at"],
                "error": job["error"],
                "job_dir": job["job_dir"],
            }

    def get_job_result(self, job_id: str) -> dict:
        """
        Return the raw output_python.txt contents for a job if present.

        Returns a dict with job_id, output_path and output (text). If the file is not
        present returns a dict with status 'no_output' and the expected output_path.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            job_dir = job.get("job_dir")

        out_path = Path(job_dir) / "output_python.txt"
        if out_path.exists():
            try:
                text = out_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                # best-effort fallback
                try:
                    text = out_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    text = ""
            return {"job_id": job_id, "output_path": str(out_path), "output": text}
        return {"job_id": job_id, "status": "no_output", "output_path": str(out_path)}

    def get_job_summary(self, job_id: str) -> dict:
        """
        Return a parsed summary (TABLE 12 / TABLE 13) from output_python.txt if present.

        Does not persist result.json; returns parsed dict or a 'no_output' status.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            job_dir = job.get("job_dir")

        out_path = Path(job_dir) / "output_python.txt"
        if out_path.exists():
            parsed = parse_output(str(out_path))
            return {"job_id": job_id, "job_dir": job_dir, "summary": parsed}
        return {"job_id": job_id, "status": "no_output", "output_path": str(out_path)}

    def list_jobs(self):
        with self._lock:
            jobs = list(self._jobs.values())
        # sort by created_at desc
        jobs = sorted(jobs, key=lambda j: j.get("created_at", 0), reverse=True)
        return [{"job_id": j["id"], "status": j["status"], "created_at": j["created_at"], "job_dir": j["job_dir"]} for j in jobs]

    def cancel_job(self, job_id: str) -> bool:
        # best-effort: if future exists, attempt to cancel
        fut = self._futures.get(job_id)
        if fut:
            ok = fut.cancel()
            if ok:
                self._update_job(job_id, status="cancelled", finished_at=time.time())
            return ok
        # otherwise mark cancelled in memory
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["status"] = "cancelled"
                job["finished_at"] = time.time()
                # persist
                self._write_metadata(job)
                return True
        return False
