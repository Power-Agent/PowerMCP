"""``run_sienna_solve`` -- run PowerSimulations.jl against a Sienna PSY-JSON system.

Sienna (PowerSystems.jl / PowerSimulations.jl) is Julia-only -- there is no
PyPI package for it. This shells out to a ``julia`` binary running
``sienna_mcp/scripts/solve_system.jl``, the same mechanism the sibling ``HOPE``
connector uses for its own Julia backend (subprocess, not ``juliacall``/``PyJulia``
-- see ``HOPE/src/hope_mcp_server/core.py``'s ``_launch_job``/``build_run_command``).

Requires the julia_bin (and optionally julia_depot_path) config keys set via
the powermcp install wizard, and PowerSystems.jl/PowerSimulations.jl/HiGHS.jl/
JSON3.jl already installed into that Julia environment -- see SIENNA/README.md
for setup steps. The open-source HiGHS solver is the only one wired up (no
vendor network call or license anywhere in this connector, per issue #54).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .._julia import run_julia_script, validate_julia_command

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "solve_system.jl"

DEFAULT_TIMEOUT_SECONDS = 1800.0


def run_sienna_solve(
    psy_json_path: str,
    solver: str = "HiGHS",
    horizon_hours: int = 24,
    output_path: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a PowerSimulations.jl economic-dispatch solve against a Sienna system.

    Builds a minimal copper-plate ProblemTemplate (ThermalBasicDispatch,
    RenewableFullDispatch, StaticPowerLoad -- whichever component types are
    present) and solves it with the open-source HiGHS solver over
    ``horizon_hours``. Returns the parsed JSON result written by the Julia
    driver script (objective value, solve status, timing) plus raw stdout/
    stderr tails for debugging. Requires Julia with PowerSystems.jl,
    PowerSimulations.jl, HiGHS.jl, and JSON3.jl installed -- see
    SIENNA/README.md.
    """
    if not SCRIPT_PATH.is_file():
        return {
            "ok": False,
            "error_type": "script_missing",
            "message": f"Julia driver script not found: {SCRIPT_PATH}",
        }

    psy_path = Path(psy_json_path).expanduser()
    if not psy_path.is_file():
        return {
            "ok": False,
            "error_type": "file_not_found",
            "message": f"PSY JSON file not found: {psy_path}",
            "path": str(psy_path),
        }

    julia_bin, julia_error = validate_julia_command()
    if julia_error is not None:
        return julia_error

    out_path = Path(output_path).expanduser() if output_path else None
    cleanup_output = False
    if out_path is None:
        fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="sienna_solve_")
        Path(tmp_name).unlink(missing_ok=True)  # let the script create it fresh
        import os as _os

        _os.close(fd)
        out_path = Path(tmp_name)
        cleanup_output = True

    script_args = [str(psy_path), str(out_path), solver, str(horizon_hours)]

    try:
        completed = run_julia_script(
            julia_bin,
            SCRIPT_PATH,
            script_args,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        return {
            "ok": False,
            "error_type": "solve_timeout",
            "message": f"run_sienna_solve timed out after {timeout_seconds}s",
            "stdout": (err.stdout or ""),
            "stderr": (err.stderr or ""),
            "command": [julia_bin, "--startup-file=no", str(SCRIPT_PATH), *script_args],
        }

    result: dict[str, Any] = {
        "exit_code": completed.returncode,
        "stdout_tail": "\n".join(completed.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(completed.stderr.splitlines()[-20:]),
        "julia_bin": julia_bin,
        "psy_json_path": str(psy_path),
    }

    if out_path.is_file():
        try:
            solve_payload = json.loads(out_path.read_text())
            result.update(solve_payload)
        except Exception as exc:
            result["ok"] = False
            result["error_type"] = "result_unparseable"
            result["message"] = f"Could not parse Julia driver output {out_path}: {exc}"
    elif "ok" not in result:
        result["ok"] = False
        result["error_type"] = "no_result_file"
        result["message"] = (
            f"Julia driver script exited {completed.returncode} without writing a result "
            f"file at {out_path}. See stdout_tail/stderr_tail."
        )

    if cleanup_output:
        out_path.unlink(missing_ok=True)
    else:
        result["output_json_path"] = str(out_path)

    return result


def register_solve_tools(mcp: FastMCP) -> None:
    """Register the Sienna solve tool with the MCP server."""
    mcp.tool(
        name="run_sienna_solve",
        description=(
            "Run a PowerSimulations.jl economic-dispatch solve (open-source HiGHS solver) "
            "against a Sienna PSY-JSON system over a Julia subprocess. Requires Julia with "
            "PowerSystems.jl/PowerSimulations.jl/HiGHS.jl/JSON3.jl installed (see "
            "SIENNA/README.md) and julia_bin configured. Returns objective value, solve "
            "status, and timing."
        ),
    )(run_sienna_solve)


__all__ = ["run_sienna_solve", "register_solve_tools"]
