"""OnSSET MCP server.

Exposes the OnSSET electrification model (https://github.com/OnSSET/onsset) to MCP clients:
input discovery and validation, calibration, scenario runs and result analysis.

The model never runs inside this process: OnSSET prints progress to stdout, which carries the
MCP protocol over stdio, and a national run takes minutes and gigabytes. Calibration and
scenario runs are started as subprocesses (``onsset_calibration.py`` / ``onsset_engine.py``)
in a per-run workspace folder and polled with ``get_run_status``. See README.md.

    python onsset_mcp.py            # stdio transport
"""

import functools
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onsset_config as cfg  # noqa: E402
import onsset_inputs as inputs  # noqa: E402
import onsset_jobs as jobs  # noqa: E402
import onsset_results as results  # noqa: E402
from onsset_params import CalibrationParams, ScenarioParams, describe_parameters as _describe  # noqa: E402

__version__ = "0.1.0"

logger = logging.getLogger("onsset_mcp")

Workflow = Literal["scenario", "calibration"]
MODELS = {"scenario": ScenarioParams, "calibration": CalibrationParams}

INSTRUCTIONS = """\
OnSSET (Open Source Spatial Electrification Tool) finds the least-cost electrification option (grid
densification/extension, mini-grids, stand-alone PV) for every settlement of a country.

Typical workflow:
1. check_environment, then list_input_files to find the settlement CSV, hourly PV and wind CSVs and MV lines.
2. A GIS-extracted CSV must be calibrated first: describe_parameters('calibration'), validate_inputs, then
   start_calibration. Its output CSV (get_run_results) is the input of scenario runs. Skip this step when
   the CSV already has FinalElecCode<start_year> (validate_inputs tells you).
3. describe_parameters('scenario') and validate_parameters; only start_year, end_year, end_year_pop and
   urban_ratio_end_year are required, everything else has a documented default.
4. validate_inputs('scenario', ...), then start_scenario_run. Runs take minutes: poll get_run_status.
5. get_run_results, inspect_result_columns, summarize_results_by and compare_runs to analyse outputs.
Run outputs live in the workspace reported by get_server_info. Never claim results for a run whose status
is not 'succeeded'."""

mcp = MCPServer("onsset", instructions=INSTRUCTIONS, version=__version__)


def _format_validation(exc):
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'params'}: {e['msg']}" for e in exc.errors())


def guarded(fn):
    """Turn expected failures into ToolErrors with a readable message, log the unexpected ones."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except ValidationError as e:
            raise ToolError(f"Invalid parameters: {_format_validation(e)}") from e
        except (ValueError, cfg.ConfigError, OSError) as e:
            raise ToolError(str(e)) from e
        except Exception as e:  # noqa: BLE001 - the server must survive any tool failure
            logger.exception("Tool %s failed", fn.__name__)
            raise ToolError(f"{type(e).__name__}: {e}") from e
    return wrapper


def tool(fn):
    return mcp.tool()(guarded(fn))


# --------------------------------------------------------------------------------------------------
# Project and environment


@tool
def get_server_info() -> dict[str, Any]:
    """Server version, configured paths (OnSSET repo, workspace, engine interpreter) and run limits."""
    repo = cfg.onsset_repo(required=False)
    return {"server": "onsset", "version": __version__,
            "server_python": sys.executable,
            "engine_python": cfg.engine_python(),
            "onsset_repo": str(repo) if repo else None,
            "workspace": str(cfg.workspace()),
            "allowed_input_roots": [str(r) for r in cfg.allowed_roots()],
            "max_concurrent_runs": cfg.max_concurrent_runs(),
            "workflows": {"calibration": str(cfg.CALIBRATION_SCRIPT), "scenario": str(cfg.ENGINE_SCRIPT)}}


_PROBE = """
import importlib, json, sys
out = {"python": sys.version.split()[0], "packages": {}}
for name in ["onsset", "pandas", "numpy", "scipy", "numba", "geopandas", "pyogrio", "shapely", "geojson",
             "pydantic"]:
    try:
        m = importlib.import_module(name)
        out["packages"][name] = getattr(m, "__version__", "installed")
        if name == "onsset":
            out["onsset_path"] = m.__file__
    except Exception as e:
        out["packages"][name] = None
        out.setdefault("errors", {})[name] = f"{type(e).__name__}: {e}"
print("ONSSET_PROBE" + json.dumps(out))
"""


@tool
def check_environment() -> dict[str, Any]:
    """Check that the engine interpreter can import OnSSET and its dependencies, and report versions,
    the OnSSET checkout and its git commit. Run this first; it takes a few seconds."""
    python = cfg.engine_python()
    proc = subprocess.run([python, "-c", _PROBE], capture_output=True, text=True, timeout=180,
                          stdin=subprocess.DEVNULL, cwd=str(cfg.HERE))
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("ONSSET_PROBE")), None)
    if line is None:
        raise ToolError(f"The engine interpreter {python} failed to start: {proc.stderr[-2000:]}")
    probe = json.loads(line[len("ONSSET_PROBE"):])
    problems = [f"{name} is not importable: {err}" for name, err in probe.get("errors", {}).items()]
    repo = cfg.onsset_repo(required=False)
    commit = None
    if repo:
        try:
            commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                                    timeout=30, stdin=subprocess.DEVNULL).stdout.strip() or None
        except OSError:
            pass
    else:
        problems.append("OnSSET checkout not found; set ONSSET_REPO.")
    for script in (cfg.ENGINE_SCRIPT, cfg.CALIBRATION_SCRIPT):
        if not script.exists():
            problems.append(f"Missing {script}")
    return {"ok": not problems, "problems": problems, "engine_python": python, **probe,
            "onsset_repo": str(repo) if repo else None, "onsset_commit": commit,
            "validated_against_commit": "486c26039ecbf8614d68da90c7b4968b2f4a5b13",
            "workspace": str(cfg.workspace())}


def _sniff(path):
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in (".shp", ".gpkg", ".geojson"):
        return "vector (MV lines candidate)" if "mv" in name or "line" in name else "vector"
    if suffix != ".csv":
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.readline() + f.readline()
    except OSError:
        return None
    if "Renewables.ninja Weather" in head:
        return "pv_hourly (renewables.ninja weather)"
    if "Renewables.ninja Wind" in head:
        return "wind_hourly (renewables.ninja wind)"
    if name.endswith("_results.csv"):
        return "scenario results"
    if name.endswith("_summaries.csv"):
        return "scenario summary"
    first = head.splitlines()[0] if head else ""
    if "GHI" in first and "X_deg" in first:
        return "settlements (calibrated)" if "FinalElecCode" in first else "settlements (GIS extract, uncalibrated)"
    return "csv"


@tool
def list_input_files(directory: str | None = None, max_depth: int = 3) -> dict[str, Any]:
    """List candidate OnSSET input files (settlement CSVs, renewables.ninja PV/wind CSVs, MV line vectors)
    with their detected role. `directory` defaults to the OnSSET repo's test/ folder; it must be inside
    an allowed root (see get_server_info). Relative paths are resolved against the OnSSET repo."""
    if directory is None:
        repo = cfg.onsset_repo()
        root = repo / "test" if (repo / "test").is_dir() else repo
    else:
        root = cfg.resolve_input(directory, "directory", kind="dir")
    if not 0 <= max_depth <= 6:
        raise ValueError("max_depth must be between 0 and 6")
    found, truncated = [], False
    for current, dirs, files in os.walk(root):
        depth = len(Path(current).relative_to(root).parts)
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "__")) and depth < max_depth)
        for fname in sorted(files):
            path = Path(current) / fname
            role = _sniff(path)
            if role is None:
                continue
            if len(found) >= 300:
                truncated = True
                break
            found.append({"path": str(path), "role": role, "bytes": path.stat().st_size})
    return {"directory": str(root), "files": found, "truncated": truncated}


# --------------------------------------------------------------------------------------------------
# Parameters and input validation


@tool
def describe_parameters(workflow: Workflow = "scenario") -> dict[str, Any]:
    """Every parameter of the 'scenario' or 'calibration' workflow, grouped, with unit, default,
    whether it is required, description and constraints."""
    model = MODELS[workflow]
    return {"workflow": workflow,
            "required": [n for n, f in model.model_fields.items() if f.is_required()],
            "groups": _describe(model)}


def _resolve(workflow, params):
    return MODELS[workflow].model_validate(params or {}).model_dump()


@tool
def validate_parameters(params: dict[str, Any], workflow: Workflow = "scenario") -> dict[str, Any]:
    """Validate parameters for a workflow without running anything. Returns the complete parameter set
    with defaults filled in (and the model time steps for a scenario), or the list of problems."""
    try:
        resolved = _resolve(workflow, params)
    except ValidationError as e:
        return {"valid": False, "errors": [f"{'.'.join(map(str, x['loc'])) or 'params'}: {x['msg']}"
                                           for x in e.errors()]}
    out = {"valid": True, "params": resolved,
           "defaulted": sorted(set(resolved) - set(params or {}))}
    if workflow == "scenario":
        targets = {**resolved["intermediate_targets"], resolved["end_year"]: resolved["end_electrification_rate_target"]}
        years = sorted(targets)
        out["time_steps"] = [{"year": y, "electrification_target": targets[y],
                              "step_years": y - (years[i - 1] if i else resolved["start_year"])}
                             for i, y in enumerate(years)]
    return out


def _check_demographics(report, p):
    """Compare the scenario's end-year population with the CSV's calibrated base year.

    OnSSET projects urban and rural growth from these two points without checks; a shrinking
    population carries the base-year electrified population over and yields rates above 100%.
    """
    pop = report["info"].get("start_year_population")
    if not pop or not p.get("end_year_pop") or not p.get("end_year") or not p.get("start_year"):
        return
    years = p["end_year"] - p["start_year"]
    if years <= 0:
        return
    growth = (p["end_year_pop"] / pop) ** (1 / years) - 1
    report["info"]["implied_annual_population_growth"] = round(growth, 5)
    if growth < 0:
        report["errors"].append(f"end_year_pop ({p['end_year_pop']:,.0f}) is below the calibrated start-year "
                                f"population of the CSV ({pop:,.0f}); OnSSET assumes growth and would report "
                                "electrification rates above 100%.")
    elif growth > 0.06:
        report["warnings"].append(f"end_year_pop implies {growth:.1%} annual growth from the CSV's start-year "
                                  f"population ({pop:,.0f}); check that both refer to the same area.")
    urban = report["info"].get("start_year_urban_ratio")
    if urban is not None and p.get("urban_ratio_end_year") is not None and \
            abs(p["urban_ratio_end_year"] - urban) > 0.3:
        report["warnings"].append(f"urban_ratio_end_year ({p['urban_ratio_end_year']}) differs strongly from the "
                                  f"start-year urban ratio of the CSV ({urban:.2f}).")
    report["ok"] = not report["errors"]


def _input_reports(workflow, input_csv, pv_csv, wind_csv, mv_lines, params):
    reports = []
    p = params or {}
    tiers = [p.get(k) for k in ("urban_target_tier", "rural_target_tier_large", "rural_target_tier_small")]
    settlements = cfg.resolve_input(input_csv, "input_csv")
    reports.append(inputs.validate_settlements(settlements, workflow, start_year=p.get("start_year"),
                                               mg_dist=p.get("mg_dist", 0.5), needs_custom_tier=6 in tiers))
    resolved = {"input_csv": str(settlements)}
    if workflow == "scenario":
        _check_demographics(reports[0], p)
        for arg, value, check in (("pv_csv", pv_csv, inputs.validate_pv), ("wind_csv", wind_csv, inputs.validate_wind),
                                  ("mv_lines", mv_lines, inputs.validate_mv_lines)):
            if not value:
                raise ValueError(f"{arg} is required for a scenario run")
            path = cfg.resolve_input(value, arg)
            resolved[arg] = str(path)
            reports.append(check(path))
        overlap = inputs.check_bounds_overlap(settlements, resolved["mv_lines"])
        if overlap:
            reports[-1]["warnings"].append(overlap)
    return resolved, reports


@tool
def validate_inputs(input_csv: str, workflow: Workflow = "scenario", pv_csv: str | None = None,
                    wind_csv: str | None = None, mv_lines: str | None = None,
                    params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Check input files against what OnSSET reads: required columns, empty and non-numeric values,
    coordinate ranges, codes; the PV file layout (renewables.ninja weather, last 8760 h after line
    341882), the wind file layout (8760 h, column 4), and the MV lines (line geometries with a CRS).
    The scenario workflow needs all four files, calibration only input_csv. Pass the intended `params`
    to also check start_year and custom-tier columns. Reading a national CSV takes 10-30 s."""
    resolved, reports = _input_reports(workflow, input_csv, pv_csv, wind_csv, mv_lines, params)
    return {"workflow": workflow, "ok": all(r["ok"] for r in reports), "files": resolved, "reports": reports}


# --------------------------------------------------------------------------------------------------
# Model runs


@tool
def start_calibration(input_csv: str, params: dict[str, Any], run_name: str, overwrite: bool = False,
                      validate: bool = True) -> dict[str, Any]:
    """Start the OnSSET calibration (base-year population, urban split, current grid and mini-grid
    electrification) of a GIS-extracted settlement CSV in the background. Writes
    <workspace>/<run_name>/OnSSET_InputFile_Calibrated.csv. Poll get_run_status. `overwrite` deletes an
    existing run folder of the same name. With `validate`, the inputs are checked first and the run is
    refused if they have errors."""
    cfg.check_run_name(run_name)
    resolved_params = _resolve("calibration", params)
    resolved, reports = _input_reports("calibration", input_csv, None, None, None, resolved_params)
    if validate and not all(r["ok"] for r in reports):
        raise ToolError("Input validation failed: " + "; ".join(e for r in reports for e in r["errors"]))
    job = jobs.start("calibration", run_name, cfg.CALIBRATION_SCRIPT,
                     ["--input-csv", resolved["input_csv"], "--params", str(jobs.params_path(run_name)),
                      "--output-dir", str(cfg.run_dir(run_name)), "--name", run_name],
                     resolved_params, resolved, overwrite=overwrite)
    return {**_job_view(job), "warnings": [w for r in reports for w in r["warnings"]],
            "next": "Poll get_run_status; when it reports 'succeeded', get_run_results gives the calibrated CSV."}


@tool
def start_scenario_run(input_csv: str, pv_csv: str, wind_csv: str, mv_lines: str, params: dict[str, Any],
                       scenario_name: str, overwrite: bool = False, validate: bool = True) -> dict[str, Any]:
    """Start an OnSSET scenario run (least-cost electrification to end_year) in the background on a
    calibrated settlement CSV, the hourly PV and wind CSVs and the existing MV lines. Outputs go to
    <workspace>/<scenario_name>/. A national run takes several minutes; poll get_run_status.
    `overwrite` deletes an existing run folder of the same name. With `validate`, the inputs are checked
    first and the run is refused if they have errors."""
    cfg.check_run_name(scenario_name)
    resolved_params = _resolve("scenario", params)
    resolved, reports = _input_reports("scenario", input_csv, pv_csv, wind_csv, mv_lines, resolved_params)
    if validate and not all(r["ok"] for r in reports):
        raise ToolError("Input validation failed: " + "; ".join(f"{r['role']}: {e}" for r in reports
                                                                 for e in r["errors"]))
    job = jobs.start("scenario", scenario_name, cfg.ENGINE_SCRIPT,
                     ["--input-csv", resolved["input_csv"], "--pv-csv", resolved["pv_csv"],
                      "--wind-csv", resolved["wind_csv"], "--mv-lines", resolved["mv_lines"],
                      "--params", str(jobs.params_path(scenario_name)),
                      "--output-dir", str(cfg.run_dir(scenario_name)), "--scenario-name", scenario_name],
                     resolved_params, resolved, overwrite=overwrite)
    return {**_job_view(job), "warnings": [w for r in reports for w in r["warnings"]],
            "next": "Poll get_run_status; when it reports 'succeeded', use get_run_results."}


def _job_view(job):
    return {k: job[k] for k in ("name", "kind", "status", "started", "directory") if k in job}


@tool
def get_run_status(run_name: str, log_lines: int = 20) -> dict[str, Any]:
    """Status of a calibration or scenario run: running, succeeded, failed, cancelled or interrupted,
    with elapsed time, the error if any, and the last `log_lines` lines of the engine log (0-200)."""
    if not 0 <= log_lines <= 200:
        raise ValueError("log_lines must be between 0 and 200")
    return jobs.status(cfg.check_run_name(run_name), log_lines)


@tool
def cancel_run(run_name: str) -> dict[str, Any]:
    """Stop a running calibration or scenario run started by this server. Its partial outputs are kept."""
    return _job_view(jobs.cancel(cfg.check_run_name(run_name)))


@tool
def list_runs() -> dict[str, Any]:
    """All calibration and scenario runs in the workspace with their status."""
    return {"workspace": str(cfg.workspace()), "runs": jobs.list_runs()}


# --------------------------------------------------------------------------------------------------
# Results


@tool
def get_run_results(run_name: str) -> dict[str, Any]:
    """Results of a succeeded run. Scenario: electrification rate per year, start-year statistics and the
    summary per final technology (population, new connections, added capacity MW, investment million USD,
    annual emissions ktCO2) plus the output files. Calibration: the modelled base-year statistics and the
    path of the calibrated CSV."""
    name = cfg.check_run_name(run_name)
    result = results.load_run(name)
    if result.get("kind") == "calibration":
        return results.calibration_summary(name)
    return results.summary(name)


@tool
def inspect_result_columns(run_name: str) -> dict[str, Any]:
    """Structure of a scenario run's settlement-level results CSV: number of settlements, per-year metrics
    (with the years available) and static columns, with units of the main metrics."""
    return results.result_columns(cfg.check_run_name(run_name))


@tool
def summarize_results_by(run_name: str, group_by: str, year: int | None = None,
                         max_groups: int = 50) -> dict[str, Any]:
    """Aggregate a scenario run's settlement results by a column (e.g. 'Admin_1' for regions or 'IsUrban')
    for one model year (default: the last): population, new connections, new capacity and investment,
    and population per final technology. Groups are sorted by population."""
    if not 1 <= max_groups <= results.MAX_GROUPS:
        raise ValueError(f"max_groups must be between 1 and {results.MAX_GROUPS}")
    return results.breakdown(cfg.check_run_name(run_name), group_by, year, max_groups)


@tool
def compare_runs(run_names: list[str]) -> dict[str, Any]:
    """Compare two or more succeeded scenario runs: final electrification rate, per-technology totals
    (population, connections, capacity, investment, emissions) and the parameters that differ."""
    return results.compare([cfg.check_run_name(n) for n in run_names])


def main():
    logging.basicConfig(level=os.environ.get("ONSSET_MCP_LOG_LEVEL", "INFO"), stream=sys.stderr,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    mcp.run()


if __name__ == "__main__":
    main()
