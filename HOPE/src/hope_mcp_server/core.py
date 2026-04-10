from __future__ import annotations

import csv
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

DEFAULT_HOPE_REPO_ROOT = Path("/Users/qianzhang/Documents/GitHub/HOPE")
DEFAULT_JULIA_COMMAND = "julia"

CASE_PATHS = {
    "md_gtep_clean": Path("ModelCases/MD_GTEP_clean_case"),
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


def setup_command(repo_root: Path, julia_command: str) -> str:
    return (
        f"{julia_command} --project={repo_root} "
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
    relative_case_path = CASE_PATHS.get(case_id)
    if relative_case_path is None:
        return None, error_result(
            "invalid_case_id",
            f"Unsupported case_id '{case_id}'. Allowed values: {', '.join(sorted(CASE_PATHS))}",
            allowed_case_ids=sorted(CASE_PATHS),
        )

    case_path = (repo_root / relative_case_path).resolve()
    if not case_path.is_dir():
        return None, error_result(
            "case_not_found",
            f"Configured case path does not exist: {case_path}",
            case_id=case_id,
            case_path=str(case_path),
            repo_root=str(repo_root),
        )
    return case_path, None


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


def looks_like_missing_hope_dependencies(stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"
    markers = (
        "required but does not seem to be installed",
        "Run `Pkg.instantiate()` to install all recorded dependencies.",
        "Package JuMP",
    )
    return any(marker in combined for marker in markers)


def build_run_command(repo_root: Path, julia_bin: str, case_path: Path) -> list[str]:
    return [
        julia_bin,
        f"--project={repo_root}",
        str(repo_root / "src" / "main.jl"),
        str(case_path),
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

    settings_path = case_path / "Settings" / "HOPE_model_settings.yml"
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


def hope_run_hope(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    repo_root = get_repo_root()
    case_path, error = resolve_case(case_id)
    if error is not None:
        return error

    julia_bin, julia_error = validate_julia_command(repo_root)
    if julia_error is not None:
        return julia_error

    command = build_run_command(repo_root, julia_bin, case_path)
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_seconds = round(time.perf_counter() - start, 3)

    if completed.returncode != 0:
        if looks_like_missing_hope_dependencies(completed.stdout, completed.stderr):
            return error_result(
                "hope_environment_not_instantiated",
                "HOPE Julia dependencies are not instantiated. Run the one-time setup command and try again.",
                case_id=case_id,
                case_path=str(case_path),
                output_path=str(output_dir_for_case(case_path)),
                exit_code=completed.returncode,
                duration_seconds=duration_seconds,
                command=command,
                setup_command=setup_command(repo_root, julia_bin),
                stderr=completed.stderr.strip(),
                stdout_tail=last_nonempty_lines(completed.stdout),
            )

        return error_result(
            "hope_run_failed",
            "HOPE run failed.",
            case_id=case_id,
            case_path=str(case_path),
            output_path=str(output_dir_for_case(case_path)),
            exit_code=completed.returncode,
            duration_seconds=duration_seconds,
            command=command,
            stderr=completed.stderr.strip(),
            stdout_tail=last_nonempty_lines(completed.stdout),
        )

    return success_result(
        case_id=case_id,
        case_path=str(case_path),
        output_path=str(output_dir_for_case(case_path)),
        exit_code=completed.returncode,
        duration_seconds=duration_seconds,
        output_summary=build_output_summary_payload(case_id, case_path),
        stdout_tail=last_nonempty_lines(completed.stdout),
    )
