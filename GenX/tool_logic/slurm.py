"""SLURM job generation and submission for GenX cases.

Everything here resolves at call time. Nothing reads the environment or the
filesystem at import, so ``import GenX.server`` works on a machine that has
never configured GenX -- the tools then fail with an actionable message
instead of the whole server failing to start.
"""

import logging
import os
import re
import shlex
import subprocess
import textwrap
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# `sbatch` is normally instant. A wedged or unreachable SLURM controller is a
# routine condition on shared clusters, and without a bound it would hang the
# whole stdio server -- one request loop, no way for the client to recover.
SBATCH_TIMEOUT_S = 60

# Job names reach an #SBATCH directive and a shell script, and SLURM itself
# only accepts a modest character set. Restricting them here means the value
# is safe long before it is quoted.
_JOB_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class GenXConfigError(RuntimeError):
    """GenX is not configured, or is configured to a path that is not there."""


def genx_dir() -> str:
    """Absolute path to the user's GenX.jl checkout.

    Resolved in the same order the rest of PowerMCP uses: the GENX_DIR
    environment variable, then ``genx.repo_root`` in ~/.powermcp/config.toml.
    """
    value = os.environ.get("GENX_DIR")
    if not value:
        try:
            from powermcp.config import get_path

            value = get_path("genx", "repo_root", must_exist=False)
        except Exception:  # powermcp absent (standalone run), or key unset
            value = None
    if not value:
        raise GenXConfigError(
            "GenX is not configured. Point it at your GenX.jl checkout with "
            "one of:\n"
            "    powermcp install                          (interactive wizard)\n"
            "    powermcp config set genx.repo_root <path>\n"
            "    set GENX_DIR=<path>                       (environment override)"
        )
    resolved = Path(value).expanduser()
    if not resolved.is_dir():
        raise GenXConfigError(f"GenX directory does not exist: {resolved}")
    return str(resolved)


def log_dir() -> str:
    """Where SLURM writes job logs. Defaults to <GENX_DIR>/run_logs."""
    return os.environ.get("GENX_LOG_DIR") or os.path.join(genx_dir(), "run_logs")


def slurm_defaults() -> dict[str, Any]:
    return {
        "partition": os.environ.get("SLURM_PARTITION", "all"),
        "cpus": int(os.environ.get("SLURM_CPUS_DEFAULT", "4")),
        # Optional: if unset, no SLURM mail lines are emitted.
        "mail_user": os.environ.get("SLURM_MAIL_USER"),
    }


def _is_valid_case(path: str) -> bool:
    return (
        os.path.isfile(os.path.join(path, "Run.jl")) and
        os.path.isfile(os.path.join(path, "settings", "genx_settings.yml"))
    )


def _contained(path: str, purpose: str) -> str:
    """Apply MCP path containment to an already-resolved path.

    Resolution has to come first: `case_dir` may be relative to the configured
    GenX directory, so only the resolved path is the one that gets opened.
    """
    try:
        from powermcp.sandbox import checked_path
    except Exception:  # standalone use without powermcp installed
        return path
    return checked_path(path, purpose=purpose)


def find_case(case_dir: str) -> str:
    # Ensures a GenX case folder resolves to a valid absolute path.
    expanded = os.path.expanduser(case_dir)
    candidates = (
        [expanded] if os.path.isabs(expanded)
        else [os.path.join(genx_dir(), expanded), os.path.abspath(expanded)]
    )
    for candidate in candidates:
        if os.path.isdir(candidate) and _is_valid_case(candidate):
            return _contained(os.path.abspath(candidate), "case_dir")

    raise ValueError(
        f"'{case_dir}' is not a valid GenX case directory "
        f"(expected Run.jl + settings/genx_settings.yml). Tried: {candidates}"
    )


def _checked_job_name(case_name: Optional[str], case_path: str) -> str:
    """Validate the job name before it reaches the generated script.

    `case_name` is a tool argument, which is to say attacker-influenced input.
    It lands in an #SBATCH directive and in shell commands, so it is checked
    against a conservative character set here and quoted at every use site
    below -- belt and braces, because a job name that slips through executes
    on the cluster under the user's own account.
    """
    name = case_name or os.path.basename(os.path.normpath(case_path))
    if not _JOB_NAME_RE.match(name):
        raise ValueError(
            f"Invalid job name {name!r}: use 1-64 characters from "
            f"[A-Za-z0-9._-]. Job names reach SLURM directives and the "
            f"generated shell script."
        )
    return name


def _positive_int(value: Any, field: str) -> int:
    number = int(value)
    if number <= 0:
        raise ValueError(f"{field} must be a positive integer, got {number}")
    return number


def build_script(
    case_path: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> str:
    job_name = _checked_job_name(case_name, case_path)
    defaults = slurm_defaults()
    partition = defaults["partition"]
    cpus = _positive_int(cpus if cpus is not None else defaults["cpus"], "cpus")
    time_hours = _positive_int(time_hours, "time_hours")
    mem_gb = _positive_int(mem_gb, "mem_gb")
    mail_user = defaults["mail_user"]

    logs = log_dir()
    root = genx_dir()

    julia_module = os.environ.get("JULIA_MODULE")        # e.g. "julia/1.10.5"
    gurobi_module = os.environ.get("GUROBI_MODULE")      # e.g. "gurobi/9.0.1"
    julia_cpu_target = os.environ.get("JULIA_CPU_TARGET")

    # Only mail when a mail user is configured.
    mail_lines = ""
    if mail_user:
        mail_lines = (
            f"#SBATCH --mail-type=BEGIN,END,FAIL\n"
            f"#SBATCH --mail-user={shlex.quote(mail_user)}\n"
        )

    cpu_target_line = ""
    if julia_cpu_target:
        cpu_target_line = f"export JULIA_CPU_TARGET={shlex.quote(julia_cpu_target)}\n"

    module_lines = ""
    if julia_module:
        module_lines += f"module load {shlex.quote(julia_module)}\n"
    if gurobi_module:
        module_lines += f"module load {shlex.quote(gurobi_module)}\n"

    header = textwrap.dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={job_name}
        #SBATCH --output={logs}/genx_case_%j.out
        #SBATCH --error={logs}/genx_case_%j.err
        #SBATCH --time={time_hours}:00:00
        #SBATCH --mem={mem_gb}G
        #SBATCH --cpus-per-task={cpus}
        #SBATCH --partition={shlex.quote(partition)}
        """)

    body = textwrap.dedent(f"""\
        export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
        {cpu_target_line}
        echo "=========================================="
        echo "Job ID: $SLURM_JOB_ID"
        echo "Case: "{shlex.quote(job_name)}
        echo "Case dir: "{shlex.quote(case_path)}
        echo "Start time: $(date)"
        echo "=========================================="

        {module_lines}
        cd {shlex.quote(case_path)}
        julia --project={shlex.quote(root)} Run.jl
        exit_code=$?

        echo ""
        echo "=========================================="
        echo "Exit code: $exit_code"
        echo "End time: $(date)"
        echo "=========================================="
        exit $exit_code
        """)

    return header + mail_lines + "\n" + body


def preview_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Generate the SLURM script for a case without submitting it (for user validation).
    Returns the script text and the resource values used.
    """
    case_path = find_case(case_dir)
    final_cpus = cpus if cpus is not None else slurm_defaults()["cpus"]
    script = build_script(case_path, time_hours, mem_gb, final_cpus, case_name=case_name)
    return {
        "success":    True,
        "case_name":  _checked_job_name(case_name, case_path),
        "case_path":  case_path,
        "time_h":     time_hours,
        "mem_gb":     mem_gb,
        "cpus":       final_cpus,
        "script":     script,
    }


def submit_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Submit a GenX case to SLURM via sbatch. Returns job_id and resource info.
    """
    case_path = find_case(case_dir)
    final_cpus = cpus if cpus is not None else slurm_defaults()["cpus"]
    script = build_script(case_path, time_hours, mem_gb, final_cpus, case_name=case_name)

    os.makedirs(log_dir(), exist_ok=True)
    try:
        result = subprocess.run(
            ["sbatch", "--parsable"],
            input=script,
            capture_output=True,
            text=True,
            timeout=SBATCH_TIMEOUT_S,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "sbatch was not found on PATH. GenX case submission needs a SLURM "
            "cluster; run this server on a login node."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"sbatch did not respond within {SBATCH_TIMEOUT_S}s. The SLURM "
            f"controller may be down; the job was not submitted."
        )

    if result.returncode != 0:
        raise RuntimeError(f"sbatch failed: {result.stderr.strip()}")

    job_id = result.stdout.strip()
    return {
        "success":    True,
        "job_id":     job_id,
        "case_name":  _checked_job_name(case_name, case_path),
        "case_path":  case_path,
        "time_h":     time_hours,
        "mem_gb":     mem_gb,
        "cpus":       final_cpus,
    }
