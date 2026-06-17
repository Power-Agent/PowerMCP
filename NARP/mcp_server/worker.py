import os
import time
import json
import subprocess
from pathlib import Path
import sys


def _call_update(target, job_id: str, **fields):
    """Call update target, which may be a callable(update_job_id, **fields) or None.

    If target is None, attempt to write metadata.json into the job folder if available
    via fields.get('job_dir'). This keeps worker usable even without a manager callback.
    """
    if callable(target):
        try:
            target(job_id, **fields)
            return
        except TypeError:
            try:
                target(job_id, fields)
                return
            except Exception:
                pass
    # fallback: write metadata.json if job_dir provided
    jd = fields.get("job_dir")
    if jd:
        try:
            p = Path(jd) / "metadata.json"
            # read existing metadata if present
            meta = {}
            if p.exists():
                try:
                    meta = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            # update fields
            meta.update(fields)
            p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass


def worker_run(job_id: str, job_dir: str, params: dict, updater=None):
    """Worker executed in separate thread/process to run narpMain and capture outputs.

    updater: optional callable(job_id, **fields) used to update manager's in-memory state.
    """
    job_dir = Path(job_dir)
    log_path = job_dir / "run.log"
    out_path = job_dir / "output_python.txt"
    result_path = job_dir / "result.json"

    _call_update(updater, job_id, job_dir=str(job_dir), status="running", started_at=time.time())

    try:
        # Ensure the subprocess can import the local package by adding the project root
        # to PYTHONPATH. Project root is the parent of this file's parent (two levels up).
        project_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(project_root) + (os.pathsep + prev if prev else "")
        # Ensure Python child process is unbuffered so logs flush promptly
        env["PYTHONUNBUFFERED"] = "1"

        # Run the narpMain script directly if available, otherwise fall back to -m invocation.
        narp_py = project_root / "reliabilityassessment" / "monte_carlo" / "narpMain.py"
        if narp_py.exists():
            cmd = [sys.executable, str(narp_py), job_dir.as_posix()]
        else:
            cmd = [sys.executable, "-m", "reliabilityassessment.monte_carlo.narpMain", job_dir.as_posix()]

        with open(log_path, "wb") as logf:
            # Prevent child from reading stdin (important when server runs over stdio)
            proc = subprocess.Popen(cmd, stdout=logf, stderr=logf, stdin=subprocess.DEVNULL, env=env)
            ret = proc.wait()
            if ret != 0:
                raise RuntimeError(f"narpMain failed with code {ret}; see {log_path}")

        # Do not parse output here. Worker will mark job completed and provide paths;
        # parsing can be done on-demand by calling get_job_result which uses parse_output.
        _call_update(
            updater,
            job_id,
            job_dir=str(job_dir),
            status="completed",
            finished_at=time.time(),
            output_path=str(out_path),
            log_path=str(log_path),
        )
    except Exception as e:
        _call_update(updater, job_id, job_dir=str(job_dir), status="failed", finished_at=time.time(), error=str(e))
        raise


def parse_output(output_file: str) -> dict:
    """Parse TABLE 12 and TABLE 13 from the narp output into a structured dict.

    Output structure:
      {
        "summary": { "A1": {"peak":..., "installed":..., "PCT_RES":..., "HLOLE":..., "EUE":..., "LOLE":...}, ... },
        "areas": [ {"area": 1, "HLOLE":..., "XLOL_hourly":..., "EUE":..., "LOLE":..., "XLOL_peak":...}, ... ]
      }

    The parser makes best-effort numeric extraction and is resilient to spacing differences.
    """
    import re

    res = {"summary": {}, "areas": []}
    txt = ""
    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except Exception:
        return res

    # --- TABLE 12 parsing: area-level hourly/peak statistics ---
    m12 = re.search(r"TABLE\s*12", txt, flags=re.I)
    if m12:
        # stop at TABLE 13 or next TABLE occurrence
        tail = txt[m12.end():]
        end_marker = re.search(r"TABLE\s*13|TABLE\s{3}13|TABLE\s+13", tail, flags=re.I)
        block = tail[:end_marker.start()] if end_marker else tail[:4000]
        for ln in block.splitlines():
            s = ln.strip()
            # lines that start with area number e.g. '1  AV' or '2  AV'
            if re.match(r"^\d+\s+\w", s):
                # collect numeric tokens from the line
                toks = re.split(r"\s+", s)
                nums = []
                for t in toks[1:]:
                    try:
                        # accept ints and floats, strip commas
                        v = float(t.replace(',', ''))
                        nums.append(v)
                    except Exception:
                        continue
                if len(nums) >= 4:
                    try:
                        area = int(re.match(r"^(\d+)", s).group(1))
                        # map numeric columns heuristically:
                        # nums[0]=HLOLE, nums[1]=XLOL_hourly, nums[2]=EUE, nums[3]=LOLE, nums[4]=XLOL_peak (if present)
                        hlole = nums[0]
                        xlol_h = nums[1] if len(nums) > 1 else None
                        eue = nums[2] if len(nums) > 2 else None
                        lole = nums[3] if len(nums) > 3 else None
                        xlol_p = nums[4] if len(nums) > 4 else None
                        res["areas"].append({
                            "area": area,
                            "HLOLE": hlole,
                            "XLOL_hourly": xlol_h,
                            "EUE": eue,
                            "LOLE": lole,
                            "XLOL_peak": xlol_p,
                        })
                    except Exception:
                        continue

    # --- TABLE 13 parsing: area summary rows like 'A1 ...' ---
    m13 = re.search(r"TABLE\s{0,3}13|TABLE\s13", txt, flags=re.I)
    if m13:
        tail = txt[m13.end():]
        block = tail[:3000]
        for ln in block.splitlines():
            s = ln.strip()
            # lines starting with A1, A2, etc.
            if re.match(r"^A\d+", s, flags=re.I):
                toks = re.split(r"\s+", s)
                nums = []
                for t in toks[1:]:
                    try:
                        v = float(t.replace(',', ''))
                        nums.append(v)
                    except Exception:
                        continue
                # heuristic mapping based on observed layout:
                # nums[0]=PEAK, nums[1]=INSTALLED, nums[2]=PCT_RES, nums[3]=HLOLE_MAGN,
                # nums[4]=HLOLE_PCT_SD, nums[5]=EUE_MAGN, nums[6]=EUE_PCT_SD, nums[7]=LOLE_MAGN, nums[8]=LOLE_PCT_SD
                try:
                    area_label = toks[0]
                    entry = {}
                    if len(nums) > 0:
                        entry["peak"] = nums[0]
                    if len(nums) > 1:
                        entry["installed"] = nums[1]
                    if len(nums) > 2:
                        entry["PCT_RES"] = nums[2]
                    if len(nums) > 3:
                        entry["HLOLE"] = nums[3]
                    if len(nums) > 5:
                        entry["EUE"] = nums[5]
                    if len(nums) > 7:
                        entry["LOLE"] = nums[7]
                    res["summary"][area_label] = entry
                except Exception:
                    continue

    return res
