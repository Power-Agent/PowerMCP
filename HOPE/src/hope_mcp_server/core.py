from __future__ import annotations

import csv
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_HOPE_REPO_ROOT = Path("/Users/qianzhang/Documents/GitHub/HOPE")
DEFAULT_JULIA_COMMAND = "julia"

DEFAULT_CASE_ID = "md_gtep_clean"
LEGACY_CASE_ALIASES = {
    DEFAULT_CASE_ID: "MD_GTEP_clean_case",
}

BOOLEAN_SETTING_KEYS = (
    "resource_aggregation",
    "endogenous_rep_day",
    "external_rep_day",
    "flexible_demand",
    "inv_dcs_bin",
    "summary_table",
    "save_postprocess_snapshot",
)


def error_result(error_type: str, message: str, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "error_type": error_type,
        "message": message,
    }
    result.update(extra)
    return result


def success_result(**payload: Any) -> dict[str, Any]:
    result = {"ok": True}
    result.update(payload)
    return result


def get_repo_root() -> Path:
    return Path(os.environ.get("HOPE_REPO_ROOT", str(DEFAULT_HOPE_REPO_ROOT))).expanduser()


def configured_julia_command() -> str:
    return os.environ.get("HOPE_JULIA_BIN", DEFAULT_JULIA_COMMAND)


def modelcases_root(repo_root: Path) -> Path:
    return repo_root / "ModelCases"


def settings_path_for_case(case_path: Path) -> Path:
    return case_path / "Settings" / "HOPE_model_settings.yml"


def is_valid_case_dir(case_path: Path) -> bool:
    return case_path.is_dir() and settings_path_for_case(case_path).is_file()


def normalize_case_identifier(value: str) -> str:
    normalized = str(value).strip().replace("\\", "/").strip("/")
    if normalized.startswith("ModelCases/"):
        normalized = normalized[len("ModelCases/") :]
    normalized = Path(normalized).name.lower()
    if normalized.endswith("_case"):
        normalized = normalized[:-5]
    return normalized


def discover_case_directories(repo_root: Path) -> dict[str, Path]:
    cases_root = modelcases_root(repo_root)
    if not cases_root.is_dir():
        return {}

    cases: dict[str, Path] = {}
    for child in sorted(cases_root.iterdir(), key=lambda path: path.name.lower()):
        if is_valid_case_dir(child):
            cases[child.name] = child.resolve()
    return cases


def list_available_case_ids(repo_root: Path) -> list[str]:
    discovered = discover_case_directories(repo_root)
    case_ids = set(discovered)
    for alias, target_dir_name in LEGACY_CASE_ALIASES.items():
        if target_dir_name in discovered:
            case_ids.add(alias)
    return sorted(case_ids)


def setup_command(repo_root: Path, julia_command: str) -> str:
    return (
        f"{julia_command} --startup-file=no --project={repo_root} "
        "-e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'"
    )


def validate_julia_command(repo_root: Path) -> tuple[str | None, dict[str, Any] | None]:
    julia_command = configured_julia_command()
    julia_env = os.environ.get("HOPE_JULIA_BIN")
    if julia_env:
        julia_path = Path(julia_env).expanduser()
        if not julia_path.is_file():
            return None, error_result(
                "julia_not_found",
                f"HOPE_JULIA_BIN does not point to a file: {julia_path}",
                setup_command=setup_command(repo_root, str(julia_path)),
                repo_root=str(repo_root),
                configured_julia_bin=str(julia_path),
            )
        if not os.access(julia_path, os.X_OK):
            return None, error_result(
                "julia_not_executable",
                f"HOPE_JULIA_BIN is not executable: {julia_path}",
                setup_command=setup_command(repo_root, str(julia_path)),
                repo_root=str(repo_root),
                configured_julia_bin=str(julia_path),
            )
        return str(julia_path), None

    resolved = shutil.which(DEFAULT_JULIA_COMMAND)
    if resolved is None:
        return None, error_result(
            "julia_not_found",
            "Julia was not found on PATH and HOPE_JULIA_BIN is not set.",
            setup_command=setup_command(repo_root, DEFAULT_JULIA_COMMAND),
            repo_root=str(repo_root),
            configured_julia_bin=DEFAULT_JULIA_COMMAND,
        )
    return resolved, None


def resolve_case(case_id: str) -> tuple[Path | None, dict[str, Any] | None]:
    repo_root = get_repo_root()
    discovered = discover_case_directories(repo_root)
    requested = str(case_id or "").strip()
    if not requested:
        return None, error_result(
            "invalid_case_id",
            "No case_id was provided. Pass a ModelCases directory name such as "
            "'USA_64zone_GTEP_case' or the legacy alias 'md_gtep_clean'.",
            allowed_case_ids=list_available_case_ids(repo_root),
            modelcases_path=str(modelcases_root(repo_root)),
        )

    trimmed = requested.replace("\\", "/").strip("/")
    if trimmed.startswith("ModelCases/"):
        trimmed = trimmed[len("ModelCases/") :]
    basename = Path(trimmed).name

    exact_candidates = (
        requested,
        trimmed,
        basename,
        LEGACY_CASE_ALIASES.get(requested),
        LEGACY_CASE_ALIASES.get(trimmed),
        LEGACY_CASE_ALIASES.get(basename),
    )
    for candidate in exact_candidates:
        if candidate and candidate in discovered:
            return discovered[candidate], None

    normalized_candidates = {
        normalize_case_identifier(requested),
        normalize_case_identifier(trimmed),
        normalize_case_identifier(basename),
    }
    normalized_matches = [
        (name, path)
        for name, path in discovered.items()
        if normalize_case_identifier(name) in normalized_candidates
    ]
    if len(normalized_matches) == 1:
        return normalized_matches[0][1], None
    if len(normalized_matches) > 1:
        return None, error_result(
            "ambiguous_case_id",
            f"Case identifier '{case_id}' matches multiple ModelCases directories.",
            case_id=case_id,
            matching_case_ids=sorted(name for name, _ in normalized_matches),
            modelcases_path=str(modelcases_root(repo_root)),
        )

    return None, error_result(
        "invalid_case_id",
        f"Unsupported case_id '{case_id}'. Use a directory name from ModelCases, "
        "for example 'USA_64zone_GTEP_case'.",
        allowed_case_ids=list_available_case_ids(repo_root),
        modelcases_path=str(modelcases_root(repo_root)),
    )


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in YAML file: {path}")
    return data


def output_dir_for_case(case_path: Path) -> Path:
    return case_path / "output"


def list_top_level_output_csvs(output_dir: Path) -> list[str]:
    if not output_dir.is_dir():
        return []
    return sorted(path.name for path in output_dir.glob("*.csv") if path.is_file())


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def last_nonempty_lines(text: str, limit: int = 20) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-limit:]


# ---------------------------------------------------------------------------
# Async job registry
# ---------------------------------------------------------------------------

@dataclass
class _Job:
    job_id: str
    command: list[str]
    process: subprocess.Popen  # type: ignore[type-arg]
    stdout_lines: list[str] = field(default_factory=list)
    stderr_lines: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.perf_counter)
    case_id: str = ""
    job_kind: str = "generic"
    include_output_summary: bool = False
    cancel_requested: bool = False
    cancelled_at: float | None = None


_jobs: dict[str, _Job] = {}


def _stream_lines(stream: Any, target: list[str]) -> None:
    for line in stream:
        target.append(line.rstrip())


def _launch_job(
    command: list[str],
    repo_root: Path,
    case_id: str = "",
    *,
    job_kind: str = "generic",
    include_output_summary: bool = False,
) -> str:
    job_id = uuid.uuid4().hex[:8]

    proc_env = _build_julia_process_env()

    process = subprocess.Popen(
        command,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=proc_env,
    )
    job = _Job(
        job_id=job_id,
        command=command,
        process=process,
        case_id=case_id,
        job_kind=job_kind,
        include_output_summary=include_output_summary,
    )
    threading.Thread(target=_stream_lines, args=(process.stdout, job.stdout_lines), daemon=True).start()
    threading.Thread(target=_stream_lines, args=(process.stderr, job.stderr_lines), daemon=True).start()
    _jobs[job_id] = job
    return job_id


def _build_julia_process_env() -> dict[str, str]:
    # Inherit the current process environment, then preserve JULIA_DEPOT_PATH
    # when Claude Desktop config points Julia to a policy-trusted depot.
    proc_env = os.environ.copy()
    julia_depot = os.environ.get("JULIA_DEPOT_PATH")
    if julia_depot:
        proc_env["JULIA_DEPOT_PATH"] = julia_depot
    return proc_env


def _parse_key_value_lines(text: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def _job_elapsed_seconds(job: _Job) -> float:
    end_time = job.cancelled_at if job.cancelled_at is not None else time.perf_counter()
    return round(end_time - job.start_time, 1)


def _job_stdout_tail(job: _Job) -> list[str]:
    return last_nonempty_lines("\n".join(job.stdout_lines))


def _job_stderr(job: _Job) -> str:
    return "\n".join(job.stderr_lines).strip()


def _job_stdout(job: _Job) -> str:
    return "\n".join(job.stdout_lines).strip()


def looks_like_missing_hope_dependencies(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"
    markers = (
        "required but does not seem to be installed",
        "Run `Pkg.instantiate()` to install all recorded dependencies.",
        "Package JuMP",
    )
    return any(marker in combined for marker in markers)


def looks_like_applocker_block(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"
    markers = (
        "Application Control policy has blocked",
        "AppLocker",
        "Error opening package file",
        "WDAC",
    )
    return any(marker in combined for marker in markers)


def julia_string_literal(value: str | Path) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def build_project_julia_command(repo_root: Path, julia_bin: str) -> list[str]:
    return [
        julia_bin,
        "--startup-file=no",
        f"--project={repo_root}",
    ]


def build_run_command(repo_root: Path, julia_bin: str, case_path: Path) -> list[str]:
    julia_script = f"using HOPE; HOPE.run_hope({julia_string_literal(case_path)})"
    return [*build_project_julia_command(repo_root, julia_bin), "-e", julia_script]


def build_debug_solver_environment_command(
    repo_root: Path,
    julia_bin: str,
    case_path: Path,
    solver: str,
) -> list[str]:
    return [
        *build_project_julia_command(repo_root, julia_bin),
        "-e",
        (
            "emit(msg) = (println(msg); flush(stdout)); "
            "emit(\"STEP=julia_start\"); "
            "emit(\"JULIA_VERSION=\" * string(VERSION)); "
            "emit(\"ACTIVE_PROJECT=\" * string(Base.active_project())); "
            "emit(\"DEPOT_PATH=\" * join(DEPOT_PATH, \";\")); "
            "emit(\"LOAD_PATH=\" * join(Base.LOAD_PATH, \";\")); "
            "emit(\"STEP=using_HOPE_start\"); "
            "using HOPE; "
            "emit(\"STEP=using_HOPE_done\"); "
            "using JuMP; "
            "emit(\"STEP=using_JuMP_done\"); "
            f"case = {julia_string_literal(case_path)}; "
            f"solver = {julia_string_literal(solver)}; "
            "emit(\"HOPE_PATH=\" * string(pathof(HOPE))); "
            "emit(\"STEP=initiate_solver_start\"); "
            "opt = HOPE.initiate_solver(case, solver); "
            "emit(\"STEP=initiate_solver_done\"); "
            "emit(\"OPTIMIZER_TYPE=\" * string(typeof(opt))); "
            "emit(\"OPTIMIZER_CONSTRUCTOR_TYPE=\" * string(typeof(getfield(opt, :optimizer_constructor)))); "
            "emit(\"OPTIMIZER_CONSTRUCTOR_VALUE=\" * string(getfield(opt, :optimizer_constructor))); "
            "emit(\"STEP=model_start\"); "
            "model = Model(opt); "
            "emit(\"STEP=model_done\"); "
            "emit(\"MODEL_TYPE=\" * string(typeof(model))); "
            "emit(\"PROBE_STATUS=ok\")"
        ),
    ]


def parse_system_cost_summary(output_dir: Path) -> tuple[float | None, list[dict[str, Any]]]:
    system_cost_path = output_dir / "system_cost.csv"
    if not system_cost_path.is_file():
        return None, []

    rows = read_csv_rows(system_cost_path)
    zone_costs: list[dict[str, Any]] = []
    total_system_cost = 0.0
    found_any_total_cost = False

    for row in rows:
        zone = row.get("Zone", "")
        inv_cost = parse_float(row.get("Inv_cost ($)"))
        opr_cost = parse_float(row.get("Opr_cost ($)"))
        loss_of_load_cost = parse_float(row.get("LoL_plt ($)"))
        total_cost = parse_float(row.get("Total_cost ($)"))
        if total_cost is not None:
            total_system_cost += total_cost
            found_any_total_cost = True

        zone_costs.append(
            {
                "zone": zone,
                "investment_cost": inv_cost,
                "operation_cost": opr_cost,
                "loss_of_load_cost": loss_of_load_cost,
                "total_cost": total_cost,
            }
        )

    return (total_system_cost if found_any_total_cost else None), zone_costs


def parse_generation_builds(output_dir: Path) -> list[dict[str, Any]]:
    capacity_path = output_dir / "capacity.csv"
    if not capacity_path.is_file():
        return []

    builds: list[dict[str, Any]] = []
    for row in read_csv_rows(capacity_path):
        ec_category = (row.get("EC_Category") or "").strip()
        final_capacity_mw = parse_float(row.get("Capacity_FIN (MW)"))
        new_build_value = parse_float(row.get("New_Build"))
        if ec_category != "Candidate":
            continue
        if (final_capacity_mw or 0.0) <= 0.0 and (new_build_value or 0.0) <= 0.0:
            continue
        builds.append(
            {
                "technology": row.get("Technology", ""),
                "zone": row.get("Zone", ""),
                "ec_category": ec_category,
                "new_build": new_build_value,
                "initial_capacity_mw": parse_float(row.get("Capacity_INI (MW)")),
                "retired_capacity_mw": parse_float(row.get("Capacity_RET (MW)")),
                "final_capacity_mw": final_capacity_mw,
            }
        )
    return builds


def parse_storage_builds(output_dir: Path) -> list[dict[str, Any]]:
    storage_path = output_dir / "es_capacity.csv"
    if not storage_path.is_file():
        return []

    builds: list[dict[str, Any]] = []
    for row in read_csv_rows(storage_path):
        ec_category = (row.get("EC_Category") or "").strip()
        energy_capacity_mwh = parse_float(row.get("EnergyCapacity (MWh)"))
        power_capacity_mw = parse_float(row.get("Capacity (MW)"))
        new_build_value = parse_float(row.get("New_Build"))
        if ec_category != "Candidate":
            continue
        if (
            (energy_capacity_mwh or 0.0) <= 0.0
            and (power_capacity_mw or 0.0) <= 0.0
            and (new_build_value or 0.0) <= 0.0
        ):
            continue
        builds.append(
            {
                "technology": row.get("Technology", ""),
                "zone": row.get("Zone", ""),
                "ec_category": ec_category,
                "new_build": new_build_value,
                "energy_capacity_mwh": energy_capacity_mwh,
                "power_capacity_mw": power_capacity_mw,
            }
        )
    return builds


def build_output_summary_payload(case_id: str, case_path: Path) -> dict[str, Any]:
    output_dir = output_dir_for_case(case_path)
    output_files = list_top_level_output_csvs(output_dir)
    total_system_cost, zone_costs = parse_system_cost_summary(output_dir)

    return {
        "case_id": case_id,
        "case_path": str(case_path),
        "output_path": str(output_dir),
        "output_exists": output_dir.is_dir(),
        "available_output_files": output_files,
        "output_file_count": len(output_files),
        "total_system_cost": total_system_cost,
        "zone_costs": zone_costs,
        "new_generation_builds": parse_generation_builds(output_dir),
        "new_storage_builds": parse_storage_builds(output_dir),
    }


def hope_case_info(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    settings_path = settings_path_for_case(case_path)
    if not settings_path.is_file():
        return error_result(
            "settings_not_found",
            f"Settings file not found: {settings_path}",
            case_id=case_id,
            case_path=str(case_path),
        )

    settings = read_yaml(settings_path)
    boolean_settings = {key: settings.get(key) for key in BOOLEAN_SETTING_KEYS}
    output_dir = output_dir_for_case(case_path)
    output_files = list_top_level_output_csvs(output_dir)

    return success_result(
        case_id=case_id,
        case_path=str(case_path),
        settings_path=str(settings_path),
        model_mode=settings.get("model_mode"),
        solver=settings.get("solver"),
        DataCase=settings.get("DataCase"),
        boolean_settings=boolean_settings,
        output_path=str(output_dir),
        output_exists=output_dir.is_dir(),
        output_csv_files=output_files,
        output_csv_count=len(output_files),
    )


def hope_output_summary(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)
    if not output_dir.is_dir():
        return error_result(
            "output_not_found",
            f"Output directory does not exist: {output_dir}",
            case_id=case_id,
            case_path=str(case_path),
            output_path=str(output_dir),
        )

    return success_result(**build_output_summary_payload(case_id, case_path))


def hope_warmup() -> dict[str, Any]:
    """Pre-compile the HOPE Julia environment so subsequent runs start fast."""
    repo_root = get_repo_root()
    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    command = [
        *build_project_julia_command(repo_root, julia_bin),
        "-e",
        "using Pkg; Pkg.instantiate(); Pkg.precompile()",
    ]
    job_id = _launch_job(command, repo_root, case_id="warmup", job_kind="warmup")
    return success_result(
        job_id=job_id,
        message=(
            "Julia HOPE warmup started in the background. "
            "Call hope_job_status with this job_id to check progress. "
            "Once complete, hope_run_hope will start much faster."
        ),
        command=command,
    )


def hope_job_status(job_id: str) -> dict[str, Any]:
    """Poll the status of a background job launched by hope_warmup or hope_run_hope."""
    job = _jobs.get(job_id)
    if job is None:
        return error_result(
            "job_not_found",
            f"No job found with id '{job_id}'. Job IDs are only valid for the current server session.",
            job_id=job_id,
        )

    exit_code = job.process.poll()
    elapsed = _job_elapsed_seconds(job)
    stdout_tail = _job_stdout_tail(job)
    stdout = _job_stdout(job)
    stderr = _job_stderr(job)

    if exit_code is None:
        return success_result(
            job_id=job_id,
            status="running",
            elapsed_seconds=elapsed,
            stdout_tail=stdout_tail,
            message=f"Job is still running ({elapsed}s elapsed). Call hope_job_status again to check.",
        )

    if job.cancel_requested:
        return success_result(
            job_id=job_id,
            status="cancelled",
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            stdout_tail=stdout_tail,
            stderr=stderr,
            message="Job was cancelled in this MCP session.",
        )

    # Job finished
    if exit_code != 0:
        stdout_joined = stdout
        if job.job_kind == "debug_probe":
            return error_result(
                "debug_probe_failed",
                "The background HOPE Julia environment probe exited with a non-zero exit code.",
                job_id=job_id,
                exit_code=exit_code,
                elapsed_seconds=elapsed,
                stdout_tail=stdout_tail,
                stdout=stdout,
                stderr=stderr,
                parsed_stdout=_parse_key_value_lines(stdout),
            )
        if looks_like_applocker_block(stdout_joined, stderr):
            return error_result(
                "applocker_blocked",
                (
                    "Windows Application Control (AppLocker/WDAC) blocked Julia's compiled cache DLLs. "
                    "Set JULIA_DEPOT_PATH in claude_desktop_config.json to a Windows-policy-trusted "
                    "directory, then run hope_warmup to rebuild the cache. On managed machines, simply "
                    "moving the depot outside C:\\Users (for example to E:\\julia_depot) may still be "
                    "blocked unless IT explicitly allows that path or the METIS DLL."
                ),
                job_id=job_id,
                exit_code=exit_code,
                elapsed_seconds=elapsed,
                stdout_tail=stdout_tail,
                stderr=stderr,
            )
        if looks_like_missing_hope_dependencies(stdout_joined, stderr):
            repo_root = get_repo_root()
            julia_bin = configured_julia_command()
            return error_result(
                "hope_environment_not_instantiated",
                "HOPE Julia dependencies are not instantiated. Call hope_warmup first, then retry.",
                job_id=job_id,
                exit_code=exit_code,
                elapsed_seconds=elapsed,
                stdout_tail=stdout_tail,
                stderr=stderr,
                setup_command=setup_command(repo_root, julia_bin),
            )
        return error_result(
            "job_failed",
            "The background job exited with a non-zero exit code.",
            job_id=job_id,
            exit_code=exit_code,
            elapsed_seconds=elapsed,
            stdout_tail=stdout_tail,
            stderr=stderr,
        )

    result = success_result(
        job_id=job_id,
        status="done",
        exit_code=exit_code,
        elapsed_seconds=elapsed,
        stdout_tail=stdout_tail,
    )
    if job.job_kind == "debug_probe":
        result["stdout"] = stdout
        result["stderr"] = stderr
        result["probe"] = _parse_key_value_lines(stdout)
        return result
    # If this was a HOPE model run, attach the output summary
    if job.include_output_summary and job.case_id:
        case_path, _ = resolve_case(job.case_id)
        if case_path is not None:
            result["output_summary"] = build_output_summary_payload(job.case_id, case_path)
    return result


def hope_cancel_job(job_id: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    """Cancel a background Julia job launched by this MCP session."""
    job = _jobs.get(job_id)
    if job is None:
        return error_result(
            "job_not_found",
            f"No job found with id '{job_id}'. Job IDs are only valid for the current server session.",
            job_id=job_id,
        )

    exit_code = job.process.poll()
    if exit_code is not None:
        status = "cancelled" if job.cancel_requested else "done"
        return success_result(
            job_id=job_id,
            status=status,
            exit_code=exit_code,
            elapsed_seconds=_job_elapsed_seconds(job),
            stdout_tail=_job_stdout_tail(job),
            stderr=_job_stderr(job),
            message=(
                "Job was already cancelled earlier in this MCP session."
                if job.cancel_requested
                else "Job has already finished; nothing was cancelled."
            ),
        )

    job.cancel_requested = True
    job.process.terminate()
    forced_kill = False

    try:
        job.process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        forced_kill = True
        job.process.kill()
        job.process.wait(timeout=timeout_seconds)

    job.cancelled_at = time.perf_counter()
    final_exit_code = job.process.poll()

    return success_result(
        job_id=job_id,
        status="cancelled",
        exit_code=final_exit_code,
        elapsed_seconds=_job_elapsed_seconds(job),
        stdout_tail=_job_stdout_tail(job),
        stderr=_job_stderr(job),
        forced_kill=forced_kill,
        message=(
            "Job was cancelled successfully."
            if not forced_kill
            else "Job did not exit after terminate(); force-killed successfully."
        ),
    )


def hope_debug_solver_environment(
    case_id: str = "md_gtep_clean",
    solver: str | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """
    Run a small Julia probe in the same environment the MCP server uses for HOPE jobs.

    This helps confirm the active project, depot path, loaded HOPE source path, and the
    actual optimizer constructor JuMP sees for the selected solver.
    """
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    settings = read_yaml(settings_path_for_case(case_path))
    selected_solver = solver or str(settings.get("solver", "highs"))
    command = build_debug_solver_environment_command(
        repo_root,
        julia_bin,
        case_path,
        selected_solver,
    )
    proc_env = _build_julia_process_env()
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=proc_env,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        stdout = (err.stdout or "").strip()
        stderr = (err.stderr or "").strip()
        return error_result(
            "debug_probe_timeout",
            "The HOPE Julia environment probe timed out.",
            case_id=case_id,
            case_path=str(case_path),
            solver=selected_solver,
            repo_root=str(repo_root),
            julia_bin=julia_bin,
            julia_depot_path=proc_env.get("JULIA_DEPOT_PATH"),
            timeout_seconds=timeout_seconds,
            command=command,
            stdout=stdout,
            stderr=stderr,
            parsed_stdout=_parse_key_value_lines(stdout),
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    parsed = _parse_key_value_lines(stdout)

    if completed.returncode != 0:
        return error_result(
            "debug_probe_failed",
            "The HOPE Julia environment probe failed.",
            case_id=case_id,
            case_path=str(case_path),
            solver=selected_solver,
            repo_root=str(repo_root),
            julia_bin=julia_bin,
            julia_depot_path=proc_env.get("JULIA_DEPOT_PATH"),
            command=command,
            stdout=stdout,
            stderr=stderr,
            parsed_stdout=parsed,
            exit_code=completed.returncode,
        )

    return success_result(
        case_id=case_id,
        case_path=str(case_path),
        solver=selected_solver,
        repo_root=str(repo_root),
        julia_bin=julia_bin,
        julia_depot_path=proc_env.get("JULIA_DEPOT_PATH"),
        command=command,
        stdout=stdout,
        stderr=stderr,
        probe=parsed,
    )


def hope_debug_solver_environment_async(
    case_id: str = "md_gtep_clean",
    solver: str | None = None,
) -> dict[str, Any]:
    """Launch the solver environment probe as a background Julia job."""
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    settings = read_yaml(settings_path_for_case(case_path))
    selected_solver = solver or str(settings.get("solver", "highs"))
    command = build_debug_solver_environment_command(
        repo_root,
        julia_bin,
        case_path,
        selected_solver,
    )
    job_id = _launch_job(
        command,
        repo_root,
        case_id=case_id,
        job_kind="debug_probe",
    )
    return success_result(
        job_id=job_id,
        case_id=case_id,
        case_path=str(case_path),
        solver=selected_solver,
        message=(
            "Background HOPE Julia environment probe started. "
            "Call hope_job_status with this job_id to inspect progress and parsed probe fields."
        ),
        command=command,
    )


def hope_run_hope(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    command = build_run_command(repo_root, julia_bin, case_path)
    job_id = _launch_job(
        command,
        repo_root,
        case_id=case_id,
        job_kind="hope_run",
        include_output_summary=True,
    )
    return success_result(
        job_id=job_id,
        message=(
            f"HOPE run started for case '{case_id}'. "
            "Call hope_job_status with this job_id to check progress. "
            "The run may take several minutes; Julia startup adds extra time on first call."
        ),
        command=command,
    )


# ---------------------------------------------------------------------------
# Settings management
# ---------------------------------------------------------------------------

# Settings keys with their allowed/type info for validation
_INT_SETTING_KEYS = {
    "carbon_policy": (0, 1, 2),
    "planning_reserve_mode": (0, 1, 2),
    "operation_reserve_mode": (0, 1, 2),
    "network_model": (0, 1, 2, 3),
    "unit_commitment": (0, 1, 2),
    "debug": (0, 1, 2),
}

_BINARY_SETTING_KEYS = (
    "resource_aggregation",
    "endogenous_rep_day",
    "external_rep_day",
    "flexible_demand",
    "inv_dcs_bin",
    "summary_table",
    "save_postprocess_snapshot",
    "clean_energy_policy",
    "transmission_expansion",
    "transmission_loss",
    "write_shadow_prices",
)

_SOLVER_OPTIONS = ("cbc", "clp", "highs", "scip", "gurobi", "cplex")
_MODEL_MODE_OPTIONS = ("GTEP", "PCM")

# Known contradictions: (key_a, value_a, key_b, value_b, message)
_CONTRADICTIONS = [
    ("network_model", 0, "write_shadow_prices", 1,
     "write_shadow_prices=1 requires network_model > 0 to recover meaningful LMPs."),
    ("network_model", 0, "transmission_loss", 1,
     "transmission_loss=1 has no effect when network_model=0 (copper plate)."),
    ("network_model", 0, "transmission_expansion", 1,
     "transmission_expansion=1 has no effect when network_model=0 (copper plate) in PCM."),
    ("endogenous_rep_day", 1, "external_rep_day", 1,
     "endogenous_rep_day and external_rep_day cannot both be 1; pick one."),
    ("unit_commitment", 0, "operation_reserve_mode", 2,
     "operation_reserve_mode=2 (NSPIN) requires unit_commitment >= 1."),
]


def hope_update_settings(
    case_id: str = "md_gtep_clean",
    changes: dict[str, Any] | None = None,
    backup: bool = True,
) -> dict[str, Any]:
    """Patch fields in a case's HOPE_model_settings.yml and return the updated settings."""
    if changes is None or len(changes) == 0:
        return error_result("no_changes", "No changes provided. Pass a non-empty 'changes' dict.")

    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    settings_path = settings_path_for_case(case_path)
    if not settings_path.is_file():
        return error_result(
            "settings_not_found",
            f"Settings file not found: {settings_path}",
            case_id=case_id,
        )

    settings = read_yaml(settings_path)

    # Optionally back up original
    if backup:
        backup_path = settings_path.with_suffix(".yml.bak")
        import shutil as _shutil
        _shutil.copy2(settings_path, backup_path)

    # Validate and apply changes
    rejected: list[dict[str, Any]] = []
    applied: dict[str, Any] = {}

    for key, value in changes.items():
        if key == "model_mode":
            if value not in _MODEL_MODE_OPTIONS:
                rejected.append({"key": key, "value": value,
                                  "reason": f"Must be one of {_MODEL_MODE_OPTIONS}"})
                continue
        elif key == "solver":
            if value not in _SOLVER_OPTIONS:
                rejected.append({"key": key, "value": value,
                                  "reason": f"Must be one of {_SOLVER_OPTIONS}"})
                continue
        elif key in _INT_SETTING_KEYS:
            allowed = _INT_SETTING_KEYS[key]
            if int(value) not in allowed:
                rejected.append({"key": key, "value": value,
                                  "reason": f"Must be one of {allowed}"})
                continue
            value = int(value)
        elif key in _BINARY_SETTING_KEYS:
            if int(value) not in (0, 1):
                rejected.append({"key": key, "value": value, "reason": "Must be 0 or 1"})
                continue
            value = int(value)

        old_value = settings.get(key)
        settings[key] = value
        applied[key] = {"old": old_value, "new": value}

    # Write updated settings
    with settings_path.open("w", encoding="utf-8") as f:
        yaml.dump(settings, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Run validation on the new settings
    warnings = _validate_settings_dict(settings)

    return success_result(
        case_id=case_id,
        settings_path=str(settings_path),
        applied=applied,
        rejected=rejected,
        validation_warnings=warnings,
        message=(
            f"Applied {len(applied)} change(s) to settings."
            + (f" Backed up original to {settings_path.with_suffix('.yml.bak')}." if backup else "")
            + (f" {len(warnings)} validation warning(s)." if warnings else "")
        ),
    )


def _validate_settings_dict(settings: dict[str, Any]) -> list[str]:
    """Return a list of warning strings for contradictory or suspicious settings."""
    warnings: list[str] = []

    for key_a, val_a, key_b, val_b, msg in _CONTRADICTIONS:
        a = settings.get(key_a)
        b = settings.get(key_b)
        if a is not None and b is not None:
            try:
                if int(a) == val_a and int(b) == val_b:
                    warnings.append(f"{key_a}={val_a} + {key_b}={val_b}: {msg}")
            except (TypeError, ValueError):
                pass

    # PCM-only flags in GTEP mode
    model_mode = settings.get("model_mode", "")
    if model_mode == "GTEP":
        for key in ("unit_commitment", "write_shadow_prices"):
            if settings.get(key, 0):
                warnings.append(
                    f"{key}=1 has no effect in GTEP mode (model_mode='GTEP')."
                )

    # Nodal model without reference_bus
    if settings.get("network_model", 0) in (2, 3) and not settings.get("reference_bus"):
        warnings.append("network_model=2 or 3 requires 'reference_bus' to be set.")

    return warnings


def hope_validate_case(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    """Check a case's settings for contradictions and suspicious combinations."""
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
    if not settings_path.is_file():
        return error_result("settings_not_found", f"Settings file not found: {settings_path}")

    settings = read_yaml(settings_path)
    warnings = _validate_settings_dict(settings)

    # Check existence of referenced solver settings file
    solver = settings.get("solver", "highs")
    solver_settings_path = case_path / "Settings" / f"{solver}_settings.yml"
    if not solver_settings_path.is_file():
        warnings.append(
            f"Solver settings file not found: Settings/{solver}_settings.yml. "
            "Solver will use default parameters."
        )

    # Check DataCase folder exists
    data_case = settings.get("DataCase", "")
    if data_case:
        data_path = case_path / data_case
        if not data_path.is_dir():
            warnings.append(f"DataCase folder does not exist: {data_path}")

    return success_result(
        case_id=case_id,
        settings_path=str(settings_path),
        model_mode=settings.get("model_mode"),
        solver=settings.get("solver"),
        DataCase=settings.get("DataCase"),
        validation_warnings=warnings,
        is_valid=len(warnings) == 0,
        message=(
            "No issues found." if not warnings
            else f"{len(warnings)} potential issue(s) detected. See 'validation_warnings'."
        ),
    )


# ---------------------------------------------------------------------------
# Output reading helpers
# ---------------------------------------------------------------------------

def hope_read_output(
    case_id: str = "md_gtep_clean",
    filename: str = "system_cost.csv",
    filters: dict[str, str] | None = None,
    max_rows: int = 200,
) -> dict[str, Any]:
    """Read any CSV from a case's output/ directory with optional column filters."""
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)
    # Allow subdirectory paths like "postprocess_snapshot/metadata.yml"
    csv_path = output_dir / filename
    if not csv_path.is_file():
        available = list_top_level_output_csvs(output_dir)
        return error_result(
            "file_not_found",
            f"Output file not found: {csv_path}",
            case_id=case_id,
            requested_file=filename,
            available_files=available,
        )

    rows = read_csv_rows(csv_path)

    # Apply column filters
    if filters:
        filtered = []
        for row in rows:
            if all(str(row.get(k, "")).strip() == str(v).strip() for k, v in filters.items()):
                filtered.append(row)
        rows = filtered

    truncated = len(rows) > max_rows
    columns = list(rows[0].keys()) if rows else []

    return success_result(
        case_id=case_id,
        filename=filename,
        columns=columns,
        row_count=len(rows),
        truncated=truncated,
        rows=rows[:max_rows],
        message=(
            f"{len(rows)} row(s) returned"
            + (" (truncated)" if truncated else "")
            + (f" after filtering by {filters}" if filters else "")
            + "."
        ),
    )


def hope_emission_compliance(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    """Parse carbon emission and RPS compliance results from a completed HOPE run."""
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)
    if not output_dir.is_dir():
        return error_result("output_not_found", f"Output directory not found: {output_dir}")

    result: dict[str, Any] = {"case_id": case_id, "ok": True}

    # --- Carbon emissions ---
    # Primary output: emissions_state.csv (State, Emissions_ton, Allowance_ton, Violation_ton, In_compliance)
    # Written by write_output.jl for both GTEP and PCM modes when carbon_policy is active.
    carbon_path = output_dir / "emissions_state.csv"
    if not carbon_path.is_file():
        # Legacy fallback name (not currently produced, but kept for future compatibility)
        carbon_path = output_dir / "carbon_emissions.csv"
    if carbon_path.is_file():
        carbon_rows = read_csv_rows(carbon_path)
        carbon_summary = []
        for row in carbon_rows:
            emissions = parse_float(
                row.get("Emissions_ton") or row.get("Emission (Ton)") or row.get("Emissions (tons)") or row.get("CO2 (tons)")
            )
            cap = parse_float(
                row.get("Allowance_ton") or row.get("Carbon_Cap (Ton)") or row.get("Allowance (tons)")
            )
            penalty = parse_float(row.get("Carbon_Penalty ($)") or row.get("Penalty ($)"))
            violation = parse_float(row.get("Violation_ton"))
            in_compliance_raw = row.get("In_compliance")
            if in_compliance_raw is not None and str(in_compliance_raw).lower() in ("true", "false"):
                in_compliance = str(in_compliance_raw).lower() == "true"
            else:
                in_compliance = (emissions is None or cap is None or emissions <= cap)
            if violation is None:
                violation = round(emissions - cap, 2) if (emissions is not None and cap is not None and emissions > cap) else 0.0
            carbon_summary.append({
                "state": row.get("State", row.get("Zone", "")),
                "emissions_tons": emissions,
                "cap_tons": cap,
                "violation_tons": violation,
                "in_compliance": in_compliance,
                "penalty_dollars": penalty,
            })
        result["carbon"] = carbon_summary
        result["carbon_violations"] = [r for r in carbon_summary if not r["in_compliance"]]
    else:
        result["carbon"] = None
        result["carbon_note"] = (
            "emissions_state.csv not found. "
            "This file is written after a successful GTEP or PCM run. "
            "Re-run the model to generate it."
        )

    # --- RPS compliance ---
    # No dedicated RPS compliance output file is currently generated by HOPE.
    # RPS is enforced as an optimization constraint; check system_cost.csv for penalty costs.
    result["rps"] = None
    result["rps_note"] = "RPS compliance output is not written to a standalone file. Check system_cost.csv for RPS penalty costs (RPS_plt column, if present)."

    total_violations = len(result.get("carbon_violations") or []) + len(result.get("rps_violations") or [])
    result["message"] = (
        "All policies in compliance." if total_violations == 0
        else f"{total_violations} compliance violation(s) found."
    )
    return result


def hope_nodal_prices(
    case_id: str = "md_gtep_clean",
    zone_or_bus: str | None = None,
    hour_start: int | None = None,
    hour_end: int | None = None,
    max_rows: int = 500,
) -> dict[str, Any]:
    """Read nodal/zonal LMPs from a completed HOPE run, with optional zone and hour filters."""
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)

    # Try nodal first, then zonal price files
    candidate_files = ["nodal_prices.csv", "zonal_prices.csv", "lmp.csv"]
    price_path: Path | None = None
    for fname in candidate_files:
        p = output_dir / fname
        if p.is_file():
            price_path = p
            break

    if price_path is None:
        available = list_top_level_output_csvs(output_dir)
        return error_result(
            "price_file_not_found",
            "No price file found. network_model must be > 0 and write_shadow_prices=1 to generate LMPs.",
            case_id=case_id,
            tried_files=candidate_files,
            available_files=available,
        )

    rows = read_csv_rows(price_path)

    # Filter by zone/bus
    if zone_or_bus is not None:
        zone_key = zone_or_bus.strip()
        rows = [
            r for r in rows
            if any(str(r.get(col, "")).strip() == zone_key
                   for col in ("Bus_id", "Zone", "Bus", "Node"))
        ]

    # Filter by hour range
    if hour_start is not None or hour_end is not None:
        def _hour(r: dict[str, str]) -> int | None:
            v = r.get("Hours") or r.get("Hour") or r.get("hours")
            return int(v) if v else None

        filtered = []
        for r in rows:
            h = _hour(r)
            if h is None:
                filtered.append(r)
                continue
            if hour_start is not None and h < hour_start:
                continue
            if hour_end is not None and h > hour_end:
                continue
            filtered.append(r)
        rows = filtered

    truncated = len(rows) > max_rows
    columns = list(rows[0].keys()) if rows else []

    return success_result(
        case_id=case_id,
        price_file=price_path.name,
        columns=columns,
        row_count=len(rows),
        truncated=truncated,
        rows=rows[:max_rows],
        message=(
            f"{len(rows)} row(s) returned from {price_path.name}"
            + (" (truncated)" if truncated else "")
            + "."
        ),
    )


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------

def hope_compare_cases(case_ids: list[str]) -> dict[str, Any]:
    """
    Compare system cost, capacity builds, and emissions across multiple cases.
    Returns side-by-side diffs for each metric.
    """
    if len(case_ids) < 2:
        return error_result("too_few_cases", "Provide at least 2 case_ids to compare.")

    resolved: list[tuple[str, Path]] = []
    for cid in case_ids:
        case_path, err = resolve_case(cid)
        if err is not None:
            return error_result(
                "invalid_case_id",
                f"Could not resolve case '{cid}': {err.get('message', '')}",
            )
        resolved.append((cid, case_path))

    comparison: dict[str, Any] = {
        "ok": True,
        "cases": case_ids,
        "system_cost": {},
        "capacity_mw_by_tech": {},
        "storage_mwh_by_tech": {},
        "total_emissions_tons": {},
    }

    for cid, case_path in resolved:
        output_dir = output_dir_for_case(case_path)

        # System cost
        total, zone_costs = parse_system_cost_summary(output_dir)
        comparison["system_cost"][cid] = {
            "total_dollars": total,
            "by_zone": zone_costs,
        }

        # Generation capacity builds (Candidate only, FIN MW)
        cap_path = output_dir / "capacity.csv"
        tech_capacity: dict[str, float] = {}
        if cap_path.is_file():
            for row in read_csv_rows(cap_path):
                tech = row.get("Technology", "Unknown")
                fin = parse_float(row.get("Capacity_FIN (MW)"))
                new_b = parse_float(row.get("New_Build", "0") or "0")
                if (fin or 0.0) > 0.0 or (new_b or 0.0) > 0.0:
                    tech_capacity[tech] = tech_capacity.get(tech, 0.0) + (fin or 0.0)
        comparison["capacity_mw_by_tech"][cid] = tech_capacity

        # Storage builds
        es_path = output_dir / "es_capacity.csv"
        stor_capacity: dict[str, float] = {}
        if es_path.is_file():
            for row in read_csv_rows(es_path):
                tech = row.get("Technology", "Unknown")
                e_mwh = parse_float(row.get("EnergyCapacity (MWh)"))
                if (e_mwh or 0.0) > 0.0:
                    stor_capacity[tech] = stor_capacity.get(tech, 0.0) + (e_mwh or 0.0)
        comparison["storage_mwh_by_tech"][cid] = stor_capacity

        # Emissions
        sys_em_path = output_dir / "system_emissions.csv"
        total_emissions: float | None = None
        if sys_em_path.is_file():
            for row in read_csv_rows(sys_em_path):
                zone = (row.get("Zone") or "").strip().lower()
                if zone in ("total", "system", "all"):
                    total_emissions = parse_float(
                        row.get("CO2 (tons)") or row.get("Emissions (tons)") or row.get("Emission (Ton)")
                    )
                    break
        comparison["total_emissions_tons"][cid] = total_emissions

    # Build diffs relative to first case
    baseline_id = case_ids[0]
    baseline_cost = comparison["system_cost"][baseline_id]["total_dollars"]
    diffs: dict[str, Any] = {}
    for cid in case_ids[1:]:
        cid_cost = comparison["system_cost"][cid]["total_dollars"]
        cost_diff = (
            round(cid_cost - baseline_cost, 2)
            if (cid_cost is not None and baseline_cost is not None)
            else None
        )
        em_base = comparison["total_emissions_tons"][baseline_id]
        em_cid = comparison["total_emissions_tons"][cid]
        em_diff = round(em_cid - em_base, 2) if (em_cid is not None and em_base is not None) else None
        diffs[f"{cid}_vs_{baseline_id}"] = {
            "cost_diff_dollars": cost_diff,
            "emissions_diff_tons": em_diff,
        }
    comparison["diffs_vs_baseline"] = diffs
    comparison["message"] = f"Compared {len(case_ids)} cases. Baseline: '{baseline_id}'."
    return comparison


# ---------------------------------------------------------------------------
# Holistic two-stage workflow
# ---------------------------------------------------------------------------

def hope_run_holistic(
    gtep_case_id: str,
    pcm_case_id: str,
) -> dict[str, Any]:
    """
    Run the two-stage GTEP→PCM holistic workflow as a background job.
    Stage 1 solves capacity expansion (GTEP); Stage 2 fixes the built fleet and runs PCM.
    Returns a job_id immediately. Poll with hope_job_status.
    """
    repo_root = get_repo_root()

    gtep_path, err = resolve_case(gtep_case_id)
    if err is not None:
        return error_result("invalid_gtep_case", err.get("message", ""), case_id=gtep_case_id)

    pcm_path, err = resolve_case(pcm_case_id)
    if err is not None:
        return error_result("invalid_pcm_case", err.get("message", ""), case_id=pcm_case_id)

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    julia_script = (
        "using HOPE; "
        f"HOPE.run_hope_holistic({julia_string_literal(gtep_path)}, "
        f"{julia_string_literal(pcm_path)})"
    )
    command = [*build_project_julia_command(repo_root, julia_bin), "-e", julia_script]

    # Tag job with both case IDs
    job_id = _launch_job(
        command,
        repo_root,
        case_id=gtep_case_id,
        job_kind="hope_run_holistic",
        include_output_summary=True,
    )
    return success_result(
        job_id=job_id,
        gtep_case_id=gtep_case_id,
        pcm_case_id=pcm_case_id,
        message=(
            f"Holistic GTEP→PCM run started (GTEP: '{gtep_case_id}', PCM: '{pcm_case_id}'). "
            "Call hope_job_status with this job_id to check progress. "
            "Stage 1 (GTEP) runs first, then Stage 2 (PCM) uses the fixed built fleet."
        ),
        command=command,
    )


# ---------------------------------------------------------------------------
# EREC postprocessing
# ---------------------------------------------------------------------------

def hope_run_erec(
    case_id: str = "md_gtep_clean",
    voll_override: float | None = None,
    delta_mw: float | None = None,
) -> dict[str, Any]:
    """
    Run EREC (Equivalent Reliability Enhancement Capability) postprocessing on a completed HOPE run.
    EREC computes how much unserved energy each resource avoids.
    Requires save_postprocess_snapshot >= 1 in HOPE_model_settings.yml.
    Returns a job_id immediately. Poll with hope_job_status.
    """
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    # Check snapshot exists
    snapshot_dir = case_path / "output" / "postprocess_snapshot"
    if not snapshot_dir.is_dir():
        settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
        settings = read_yaml(settings_path) if settings_path.is_file() else {}
        snap_val = settings.get("save_postprocess_snapshot", 0)
        return error_result(
            "snapshot_not_found",
            f"Postprocess snapshot directory not found: {snapshot_dir}. "
            f"Set save_postprocess_snapshot >= 1 in HOPE_model_settings.yml and re-run the case first. "
            f"Current value: save_postprocess_snapshot={snap_val}.",
            case_id=case_id,
            snapshot_path=str(snapshot_dir),
        )

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    # Build EREC overrides string
    overrides: list[str] = []
    if voll_override is not None:
        overrides.append(f'"voll_override" => {voll_override}')
    if delta_mw is not None:
        overrides.append(f'"delta_mw" => {delta_mw}')

    overrides_str = "Dict(" + ", ".join(overrides) + ")" if overrides else "Dict()"

    julia_script = (
        "using HOPE; "
        f"HOPE.calculate_erec({julia_string_literal(case_path)}, overrides={overrides_str})"
    )
    command = [*build_project_julia_command(repo_root, julia_bin), "-e", julia_script]

    job_id = _launch_job(
        command,
        repo_root,
        case_id=case_id,
        job_kind="hope_run_erec",
        include_output_summary=True,
    )
    return success_result(
        job_id=job_id,
        case_id=case_id,
        snapshot_path=str(snapshot_dir),
        voll_override=voll_override,
        delta_mw=delta_mw,
        message=(
            f"EREC postprocessing started for case '{case_id}'. "
            "Call hope_job_status to check progress. "
            "Results will be saved under output/output_erec/ when complete."
        ),
        command=command,
    )


# ---------------------------------------------------------------------------
# Representative-day & aggregation audits (Python-side, no Julia needed)
# ---------------------------------------------------------------------------

def hope_rep_day_audit(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    """
    Summarize representative-period clustering results from a completed HOPE run.
    Returns period assignments, weights, and compression ratio (8760 → N hours).
    """
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)

    # Check settings to confirm rep-day was enabled
    settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
    settings = read_yaml(settings_path) if settings_path.is_file() else {}
    endo = settings.get("endogenous_rep_day", 0)
    exo = settings.get("external_rep_day", 0)

    if not endo and not exo:
        return error_result(
            "rep_day_disabled",
            "Representative-day mode is disabled in this case "
            "(endogenous_rep_day=0 and external_rep_day=0). "
            "Enable endogenous_rep_day=1 and re-run to generate clustering audit files.",
            case_id=case_id,
        )

    result: dict[str, Any] = {"ok": True, "case_id": case_id}

    # Metadata
    meta_path = output_dir / "representative_period_metadata.csv"
    if meta_path.is_file():
        meta_rows = read_csv_rows(meta_path)
        result["periods"] = meta_rows
        result["n_periods"] = len(meta_rows)
        total_weight = sum(
            parse_float(r.get("WeightDays") or r.get("Weight")) or 0.0 for r in meta_rows
        )
        result["total_weight_days"] = total_weight
    else:
        result["periods"] = None
        result["note_metadata"] = "representative_period_metadata.csv not found."

    # Assignments (day-of-year → period)
    assign_path = output_dir / "representative_period_assignments.csv"
    if assign_path.is_file():
        assign_rows = read_csv_rows(assign_path)
        result["assignments"] = assign_rows
        result["n_days_assigned"] = len(assign_rows)
    else:
        result["assignments"] = None

    # Weight check
    check_path = output_dir / "representative_period_weight_check.csv"
    if check_path.is_file():
        result["weight_check"] = read_csv_rows(check_path)

    # Compute compression ratio
    n_periods = result.get("n_periods")
    if n_periods and n_periods > 0:
        # Each representative period typically consists of representative_days_per_period days × 24h
        rep_days_per_period = settings.get("representative_days_per_period", 2)
        rep_hours = n_periods * rep_days_per_period * 24
        result["compression_ratio"] = round(8760 / rep_hours, 2)
        result["representative_hours"] = rep_hours
        result["full_year_hours"] = 8760
        result["message"] = (
            f"{n_periods} period(s), ~{rep_hours} representative hours "
            f"(compression ratio {result['compression_ratio']}× vs full 8760-hour year)."
        )
    else:
        result["message"] = "Period metadata not available."

    return result


def hope_aggregation_audit(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    """
    Summarize resource aggregation results from a completed HOPE run.
    Returns the raw→aggregated generator mapping and reduction statistics.
    """
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    output_dir = output_dir_for_case(case_path)

    # Check settings
    settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
    settings = read_yaml(settings_path) if settings_path.is_file() else {}
    agg_enabled = settings.get("resource_aggregation", 0)

    if not agg_enabled:
        return error_result(
            "aggregation_disabled",
            "Resource aggregation is disabled in this case (resource_aggregation=0). "
            "Enable resource_aggregation=1 and re-run to generate audit files.",
            case_id=case_id,
        )

    result: dict[str, Any] = {"ok": True, "case_id": case_id}

    # Mapping file
    mapping_path = output_dir / "resource_aggregation_mapping.csv"
    if mapping_path.is_file():
        mapping_rows = read_csv_rows(mapping_path)
        result["mapping"] = mapping_rows
        result["n_raw_resources"] = len({r.get("RawResource", r.get("Raw_Resource", "")) for r in mapping_rows})
        result["n_aggregated_resources"] = len({r.get("AggregatedResource", r.get("Aggregated_Resource", "")) for r in mapping_rows})
    else:
        result["mapping"] = None
        result["note_mapping"] = "resource_aggregation_mapping.csv not found."

    # Summary file
    summary_path = output_dir / "resource_aggregation_summary.csv"
    if summary_path.is_file():
        summary_rows = read_csv_rows(summary_path)
        result["summary"] = summary_rows
        n_agg = len(summary_rows)

        # Compute total original and aggregated capacity
        total_pmax_orig = sum(
            parse_float(r.get("Pmax_Original (MW)") or r.get("Pmax_Original")) or 0.0
            for r in summary_rows
        )
        total_pmax_agg = sum(
            parse_float(r.get("Pmax_Aggregated (MW)") or r.get("Pmax_Aggregated")) or 0.0
            for r in summary_rows
        )
        result["total_pmax_original_mw"] = round(total_pmax_orig, 2)
        result["total_pmax_aggregated_mw"] = round(total_pmax_agg, 2)
        result["n_aggregated_resources"] = n_agg
    else:
        result["summary"] = None
        result["note_summary"] = "resource_aggregation_summary.csv not found."

    # Compute reduction
    n_raw = result.get("n_raw_resources")
    n_agg = result.get("n_aggregated_resources")
    if n_raw and n_agg:
        result["reduction_ratio"] = round(n_raw / n_agg, 2)
        result["message"] = (
            f"Aggregated {n_raw} raw resources → {n_agg} clusters "
            f"({result['reduction_ratio']}× reduction)."
        )
    else:
        result["message"] = "Aggregation audit files not found in output directory."

    # Check aggregation settings file
    agg_settings_path = case_path / "Settings" / "HOPE_aggregation_settings.yml"
    if agg_settings_path.is_file():
        agg_settings = read_yaml(agg_settings_path)
        result["aggregation_settings"] = {
            "method": agg_settings.get("aggregation_method", "basic"),
            "grouping_keys": agg_settings.get("grouping_keys"),
            "clustering_target_cluster_size": agg_settings.get("clustering_target_cluster_size"),
        }

    return result


# ---------------------------------------------------------------------------
# Dashboard launcher
# ---------------------------------------------------------------------------

@dataclass
class DashboardProcessInfo:
    process: subprocess.Popen  # type: ignore[type-arg]
    log_path: Path
    command: str


# Registry of dashboard subprocesses keyed by port number.
_dashboard_procs: dict[int, DashboardProcessInfo] = {}


def _port_in_use(port: int) -> bool:
    """Return True if something is already listening on 127.0.0.1:<port>."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port: int, timeout_seconds: float = 15.0) -> bool:
    """Poll until a local TCP port is listening or timeout expires."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _port_in_use(port):
            return True
        time.sleep(0.25)
    return _port_in_use(port)


def _dashboard_logs_dir(dashboard_dir: Path) -> Path:
    logs_dir = dashboard_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _tail_text_file(path: Path, max_lines: int = 40) -> list[str]:
    if not path.is_file():
        return []
    try:
        return last_nonempty_lines(path.read_text(encoding="utf-8", errors="ignore"), max_lines)
    except Exception as exc:
        return [f"Failed to read log file {path}: {exc}"]


def _dashboard_launch_env(repo_root: Path, effective_port: int) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        upper_key = key.upper()
        if upper_key in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP"}:
            env.pop(key, None)
            continue
        if upper_key.startswith("UV_"):
            env.pop(key, None)
    env["HOPE_MODELCASES_PATH"] = str(repo_root / "ModelCases")
    env["HOPE_DASHBOARD_PORT"] = str(effective_port)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _dashboard_log_path(dashboard_dir: Path, model_mode: str, effective_port: int) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    slug = model_mode.lower()
    return _dashboard_logs_dir(dashboard_dir) / f"{slug}-dashboard-{effective_port}-{timestamp}.log"


def _dashboard_runner_command(repo_root: Path, python_bin: str, runner_script: Path) -> str:
    try:
        runner_arg = str(runner_script.relative_to(repo_root))
    except ValueError:
        runner_arg = str(runner_script)
    return subprocess.list2cmdline([python_bin, runner_arg])


def _find_python_for_dashboard() -> str:
    """Find a suitable Python executable that can run the Dash dashboard.

    Search order:
    1. ``HOPE_PYTHON_BIN`` environment variable (explicit override)
    2. Well-known Python 3.12 path written into ``start_dashboard.bat``
    3. ``python`` on PATH
    4. Current interpreter (``sys.executable``) as a last resort
    """
    hope_py = os.environ.get("HOPE_PYTHON_BIN")
    if hope_py:
        return hope_py

    # Path baked into start_dashboard.bat for this machine
    known = Path(r"C:\Users\wangs\AppData\Local\Programs\Python\Python312\python.exe")
    if known.is_file():
        return str(known)

    on_path = shutil.which("python")
    if on_path:
        return on_path

    return sys.executable


def hope_open_dashboard(
    case_id: str = "md_gtep_clean",
    port: int | None = None,
) -> dict[str, Any]:
    """Launch the local HOPE Dash dashboard for a completed case run.

    Automatically selects the GTEP dashboard (port 8051) for GTEP cases and the
    PCM dashboard (port 8050) for PCM cases based on ``model_mode`` in
    ``HOPE_model_settings.yml``.

    If a dashboard is already running on the target port, the existing URL is
    returned immediately without starting a new process.

    The dashboard reads all ModelCases from the local repository.  After opening
    the browser URL, select the matching case from the dropdown in the UI.

    If the dashboard dependencies (dash, plotly, pandas …) are not installed in
    the Python environment found, the tool returns a ``dashboard_crashed`` error
    with the install command.
    """
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    # Determine model mode from settings (default GTEP)
    settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
    model_mode = "GTEP"
    if settings_path.is_file():
        try:
            settings = read_yaml(settings_path)
            model_mode = (settings.get("model_mode") or "GTEP").upper().strip()
        except Exception:
            pass

    dashboard_dir = repo_root / "tools" / "hope_dashboard"
    if model_mode == "PCM":
        runner_script = dashboard_dir / "run_dashboard.py"
        default_port = 8050
        app_label = "PCM Dashboard"
    else:
        runner_script = dashboard_dir / "run_gtep_dashboard.py"
        default_port = 8051
        app_label = "GTEP Dashboard"

    if not runner_script.is_file():
        return error_result(
            "dashboard_script_not_found",
            f"Dashboard runner script not found: {runner_script}. "
            "Ensure the tools/hope_dashboard directory is present in the repository.",
            dashboard_dir=str(dashboard_dir),
            runner_script=str(runner_script),
        )

    effective_port = port if port is not None else default_port
    url = f"http://127.0.0.1:{effective_port}"

    # --- Check if a dashboard is already running on this port ---
    if _port_in_use(effective_port):
        existing = _dashboard_procs.get(effective_port)
        if existing is not None and existing.process.poll() is None:
            status = "running"
        else:
            status = "already_running_external"
        case_rel = str(case_path.relative_to(repo_root))
        return success_result(
            url=url,
            status=status,
            port=effective_port,
            model_mode=model_mode,
            case_id=case_id,
            message=(
                f"{app_label} is already running at {url}. "
                f"Open that URL in your browser and select '{case_rel}' from the case dropdown."
            ),
        )

    python_bin = _find_python_for_dashboard()
    env = _dashboard_launch_env(repo_root, effective_port)
    log_path = _dashboard_log_path(dashboard_dir, model_mode, effective_port)
    launch_command = _dashboard_runner_command(repo_root, python_bin, runner_script)
    cmd_exe = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")

    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"[launcher] cwd={repo_root}\n")
        log_handle.write(f"[launcher] command={launch_command}\n")
        log_handle.write(f"[launcher] port={effective_port}\n")
        log_handle.flush()
        # On Windows, launching through cmd.exe from the repo root mirrors the
        # manual dashboard command that works reliably in Command Prompt and
        # Claude Desktop. Direct Python subprocess launches proved more brittle
        # under the MCP server environment.
        process = subprocess.Popen(
            [cmd_exe, "/d", "/c", launch_command],
            cwd=str(repo_root),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )

    _dashboard_procs[effective_port] = DashboardProcessInfo(
        process=process,
        log_path=log_path,
        command=launch_command,
    )

    # Give Dash time to import data-heavy dashboards and bind the HTTP port.
    if _wait_for_port(effective_port, timeout_seconds=45.0):
        case_rel = str(case_path.relative_to(repo_root))
        return success_result(
            url=url,
            status="running",
            pid=process.pid,
            model_mode=model_mode,
            case_id=case_id,
            port=effective_port,
            python_bin=python_bin,
            log_path=str(log_path),
            launch_command=launch_command,
            message=(
                f"{app_label} is running at {url}. "
                f"Open that URL in your browser. "
                f"In the case selector, choose '{case_rel}' to view results for case '{case_id}'. "
                f"Startup log: {log_path}"
            ),
        )

    if process.poll() is not None:
        return error_result(
            "dashboard_crashed",
            f"Dashboard process exited immediately (exit code {process.returncode}). "
            "Ensure dashboard dependencies are installed: "
            f"cd tools/hope_dashboard && {python_bin} -m pip install -r requirements.txt",
            exit_code=process.returncode,
            stdout_tail=_tail_text_file(log_path),
            stderr_tail=[],
            python_bin=python_bin,
            log_path=str(log_path),
            launch_command=launch_command,
            install_command=(
                f"cd {dashboard_dir} && "
                f"{python_bin} -m pip install -r requirements.txt"
            ),
        )

    case_rel = str(case_path.relative_to(repo_root))
    return error_result(
        "dashboard_start_timeout",
        f"{app_label} process started (PID {process.pid}) but did not open {url} within 45 seconds.",
        pid=process.pid,
        url=url,
        port=effective_port,
        model_mode=model_mode,
        case_id=case_id,
        python_bin=python_bin,
        stdout_tail=_tail_text_file(log_path),
        stderr_tail=[],
        log_path=str(log_path),
        launch_command=launch_command,
        startup_hint=(
            f"{app_label} is still starting or hung before binding {url}. "
            f"If it eventually opens, select '{case_rel}' in the case dropdown."
        ),
    )


def hope_close_dashboard(port: int | None = None) -> dict[str, Any]:
    """Stop a running HOPE dashboard subprocess.

    If ``port`` is given, stop only the dashboard on that port.
    If omitted, stop all dashboards tracked by this server session.

    Only dashboards started by ``hope_open_dashboard`` in the current server
    session can be stopped this way (the process must be in the internal
    registry).  Externally-started Dash servers on the same port are not
    affected.
    """
    if not _dashboard_procs:
        return success_result(
            stopped=[],
            message="No dashboard processes are currently tracked by this session.",
        )

    targets: dict[int, DashboardProcessInfo] = {}
    if port is not None:
        info = _dashboard_procs.get(port)
        if info is None:
            return error_result(
                "dashboard_not_found",
                f"No dashboard tracked on port {port}. "
                f"Currently tracked ports: {sorted(_dashboard_procs)}.",
                tracked_ports=sorted(_dashboard_procs),
            )
        targets[port] = info
    else:
        targets = dict(_dashboard_procs)

    stopped: list[dict[str, Any]] = []
    for p, info in targets.items():
        proc = info.process
        already_dead = proc.poll() is not None
        if not already_dead:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        exit_code = proc.poll()
        _dashboard_procs.pop(p, None)
        stopped.append({
            "port": p,
            "pid": proc.pid,
            "exit_code": exit_code,
            "was_already_dead": already_dead,
            "log_path": str(info.log_path),
            "launch_command": info.command,
        })

    ports_str = ", ".join(str(s["port"]) for s in stopped)
    return success_result(
        stopped=stopped,
        message=f"Stopped dashboard(s) on port(s): {ports_str}.",
    )
