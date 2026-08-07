"""Julia process helpers for the SIENNA connector.

Mirrors the mechanism ``HOPE`` (this repo's other Julia-backed connector) uses:
Sienna (PowerSystems.jl / PowerSimulations.jl) is not on PyPI, so we shell out to
a ``julia`` binary rather than embedding it via ``juliacall``/``PyJulia``. See
``HOPE/src/hope_mcp_server/core.py`` (``_hope_setting``, ``_build_julia_process_env``,
``validate_julia_command``) for the precedent this file follows.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_JULIA_COMMAND = "julia"


def _sienna_setting(env_var: str, config_key: str, default: Any) -> Any:
    """Resolve a SIENNA setting in order: env var, powermcp config, default.

    The powermcp import is wrapped in try/except so this connector stays runnable
    standalone (e.g. ``python -m sienna_mcp``) without powermcp installed; on any
    failure we fall back to the given default.
    """
    v = os.environ.get(env_var)
    if v:
        return v
    try:
        from powermcp.config import get_path

        return get_path("sienna", config_key, must_exist=False)
    except Exception:
        return default


def configured_julia_command() -> str:
    return _sienna_setting("SIENNA_JULIA_BIN", "julia_bin", DEFAULT_JULIA_COMMAND)


def configured_julia_depot_path() -> str:
    return _sienna_setting("JULIA_DEPOT_PATH", "julia_depot_path", "")


def validate_julia_command() -> tuple[str | None, dict[str, Any] | None]:
    """Resolve and sanity-check the configured Julia binary.

    Returns ``(julia_path, None)`` on success or ``(None, error_dict)`` on failure.
    """
    julia_command = configured_julia_command()
    julia_env = julia_command if julia_command != DEFAULT_JULIA_COMMAND else None
    if julia_env:
        julia_path = Path(julia_env).expanduser()
        if not julia_path.is_file():
            return None, {
                "ok": False,
                "error_type": "julia_not_found",
                "message": f"julia_bin does not point to a file: {julia_path}",
                "configured_julia_bin": str(julia_path),
            }
        if not os.access(julia_path, os.X_OK):
            return None, {
                "ok": False,
                "error_type": "julia_not_executable",
                "message": f"julia_bin is not executable: {julia_path}",
                "configured_julia_bin": str(julia_path),
            }
        return str(julia_path), None

    resolved = shutil.which(DEFAULT_JULIA_COMMAND)
    if resolved is None:
        return None, {
            "ok": False,
            "error_type": "julia_not_found",
            "message": (
                "Julia was not found on PATH and no julia_bin is configured. "
                "Set it via the powermcp install wizard, SIENNA_JULIA_BIN, or config.toml "
                "([sienna].julia_bin)."
            ),
        }
    return resolved, None


def build_julia_process_env() -> dict[str, str]:
    """Inherit the current environment, overriding JULIA_DEPOT_PATH if configured."""
    proc_env = os.environ.copy()
    depot = configured_julia_depot_path()
    if depot:
        proc_env["JULIA_DEPOT_PATH"] = depot
    return proc_env


def julia_string_literal(value: str | Path) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def run_julia_script(
    julia_bin: str,
    script_path: Path,
    script_args: list[str],
    *,
    timeout_seconds: float,
    project_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Julia script file as a subprocess and return the completed process.

    Raises ``subprocess.TimeoutExpired`` on timeout (the caller decides how to
    report it); does not raise on a non-zero exit code.
    """
    command = [julia_bin, "--startup-file=no"]
    if project_dir is not None:
        command.append(f"--project={project_dir}")
    command += [str(script_path), *script_args]

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=build_julia_process_env(),
        timeout=timeout_seconds,
    )
