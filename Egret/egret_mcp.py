import sys
import os
from mcp.server.mcpserver import MCPServer as FastMCP
from egret.data.model_data import ModelData
from egret.models.unit_commitment import solve_unit_commitment
from egret.models.acopf import solve_acopf, create_psv_acopf_model
from egret.models.dcopf import solve_dcopf, create_ptdf_dcopf_model
from typing import Dict, Any, Optional
import io
import logging
from contextlib import redirect_stdout, redirect_stderr
import numpy as np

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.solver_case import resolve_solver_case
    from powermcp.sandbox import (
        PathNotAllowed,
        checked_path,
        ensure_checked_directory,
        staged_file_write,
    )
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

# Configure logging to be less verbose
logging.getLogger('egret').setLevel(logging.WARNING)
logging.getLogger('numexpr').setLevel(logging.WARNING)
logging.getLogger('pyomo').setLevel(logging.WARNING)

# Create an MCP server
mcp = FastMCP("Egret Power System Analysis Server")

@mcp.tool()
def solve_unit_commitment_problem(
    case_file: str,
    solver: str = "gurobi",
    mipgap: float = 0.01,
    timelimit: int = 300
) -> Dict[str, Any]:
    """Solve a unit commitment problem using Egret
    
    Args:
        case_file: Path to the case file in Egret JSON format
        solver: Solver to use (default: gurobi)
        mipgap: MIP gap tolerance (default: 0.01)
        timelimit: Time limit in seconds (default: 300)
    
    Returns:
        Dict containing the solution results
    """
    try:
        case_file = checked_path(case_file, purpose="case_file")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        # Completely capture both stdout and stderr
        f_out = io.StringIO()
        f_err = io.StringIO()
        
        with redirect_stdout(f_out), redirect_stderr(f_err):
            # Load the case file
            md = ModelData.read(case_file)
            
            # Solve the unit commitment problem with solver_tee=False to silence solver output
            md_sol = solve_unit_commitment(
                md,
                solver,
                mipgap=mipgap,
                timelimit=timelimit,
                solver_tee=False  # Explicitly disable solver output
            )
        
        # Extract key results
        results = {
            "status": "success",
            "total_cost": md_sol.data['system']['total_cost'],
            "solution": md_sol.data,
            # Include captured output for debugging if needed
            "stdout": f_out.getvalue(),
            "stderr": f_err.getvalue()
        }
        
        return results
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def solve_ac_opf(
    case_file: str,
    solver: str = "ipopt",
    return_results: bool = True
) -> Dict[str, Any]:
    """Solve an AC Optimal Power Flow problem using Egret
    
    Args:
        case_file: Path to the case file (can be Matpower or Egret JSON format)
        solver: Solver to use (default: ipopt)
        return_results: Whether to return detailed results (default: True)
    
    Returns:
        Dict containing the solution results
    """
    try:
        case_file = checked_path(case_file, purpose="case_file")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        # Completely capture both stdout and stderr
        f_out = io.StringIO()
        f_err = io.StringIO()
        
        with redirect_stdout(f_out), redirect_stderr(f_err):
            # Load the case file
            md = ModelData.read(case_file)
            
            # Solve AC OPF with solver_tee=False to silence solver output
            md_sol, results = solve_acopf(
                md,
                solver,
                acopf_model_generator=create_psv_acopf_model,
                return_results=return_results,
                solver_tee=False  # Explicitly disable solver output
            )
        
        # Extract key results
        solution = {
            "status": "success",
            "objective_value": results["Solution"][0]["Objective"]["f"],
            "termination_condition": str(results["Solver"][0]["Termination condition"]),
            "solution": md_sol.data,
            # Include captured output for debugging if needed
            "stdout": f_out.getvalue(),
            "stderr": f_err.getvalue()
        }
        
        return solution
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def solve_dc_opf(
    case_file: str,
    solver: str = "gurobi",
    return_results: bool = True
) -> Dict[str, Any]:
    """Solve a DC Optimal Power Flow problem using Egret
    
    Args:
        case_file: Path to the case file (can be Matpower or Egret JSON format)
        solver: Solver to use (default: gurobi)
        return_results: Whether to return detailed results (default: True)
    
    Returns:
        Dict containing the solution results
    """
    try:
        case_file = checked_path(case_file, purpose="case_file")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        # Completely capture both stdout and stderr
        f_out = io.StringIO()
        f_err = io.StringIO()
        
        with redirect_stdout(f_out), redirect_stderr(f_err):
            # Load the case file
            md = ModelData.read(case_file)
            
            # Solve DC OPF with solver_tee=False to silence solver output
            md_sol, results = solve_dcopf(
                md,
                solver,
                dcopf_model_generator=create_ptdf_dcopf_model,
                return_results=return_results,
                solver_tee=False  # Explicitly disable solver output
            )
        
        # Extract key results
        solution = {
            "status": "success",
            "solution": md_sol.data
        }
        
        if return_results:
            solution["solver_results"] = results
            
        # Include captured output for debugging if needed
        solution["stdout"] = f_out.getvalue()
        solution["stderr"] = f_err.getvalue()
            
        return solution
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# ---------------------------------------------------------------------------
# PowerIO interchange: resolve one balanced state, convert it to Egret JSON, and
# stage the file consumed by the solver tools above.
# ---------------------------------------------------------------------------


def _ensure_egret_runs_dir() -> str:
    from powermcp.paths import runs_dir

    return ensure_checked_directory(
        str(runs_dir("egret", create=False)),
        purpose="generated Egret output root",
    )


def _stage_egret_model(egret_json_text: str):
    """Validate egret JSON by constructing a ModelData from the parsed dict,
    stage it to a temp file the solver tools can read, and summarize it."""
    import json
    import pathlib
    import tempfile

    def write(staging: str) -> None:
        with open(staging, "w", encoding="utf-8") as fh:
            fh.write(egret_json_text)

    md = ModelData(json.loads(egret_json_text))
    fd, path = tempfile.mkstemp(
        suffix=".json", prefix="egret_case_", dir=_ensure_egret_runs_dir()
    )
    os.close(fd)
    try:
        path = checked_path(
            path, purpose="generated Egret case path", for_write=True
        )
        # mkstemp reserves the name; the model text replaces it in one step, so
        # the path a solver tool receives holds the whole case or nothing.
        staged_file_write(path, True, write)
    except BaseException:
        pathlib.Path(path).unlink(missing_ok=True)
        raise
    info = {name: len(items) for name, items in md.data.get("elements", {}).items()}
    return path, info


@mcp.tool()
def load_model_from_any(
    file_path: str,
    source_format: Optional[str] = None,
    operating_point: Optional[int] = None,
    study_commit: Optional[int] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    edits: str = "",
    to_balanced: bool = False,
    base_mva: float = 100.0,
) -> Dict[str, Any]:
    """Convert any powerio readable case file into an egret model.

    Reads any balanced PowerIO format or a ``.pio.json`` module, converts one
    selected state to Egret JSON, validates it as ModelData, and stages it. For
    a TimeSeries, select time_index; for a ScenarioSet, select scenario_id. Pass the returned `case_file` path to solve_ac_opf, solve_dc_opf, or
    solve_unit_commitment_problem. powerio is a core dependency, so this is
    always available.

    Args:
        file_path: Path to the case file
        source_format: Input format name (matpower, powermodels-json,
            egret-json, psse, powerworld); inferred from the file extension
            when omitted
        operating_point: Compatibility alias for time_index
        study_commit: Retired package selector; export a Tellegen Study state as IR
        time_index: Explicit TimeSeries index
        scenario_id: Explicit ScenarioSet identifier
        edits: JSON list of typed what-if edits PowerIO applies before the
            conversion, in list order, for example
            [{"op": "set_load_active_power", "load": "loads:0", "mw": 91.5}]
            Consecutive updates of one class apply as one atomic batch, and a
            bus load reallocation sees the values the edits before it produced.
        to_balanced: Authorize the multiconductor to balanced transformation;
            the response carries its readiness report as `lowering`
        base_mva: System base for that transformation

    Returns:
        Dict with status, the staged `case_file` path, model element counts,
        and powerio's fidelity warnings
    """
    try:
        file_path = checked_path(file_path, purpose="file_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        prepared = resolve_solver_case(
            file_path=file_path,
            source_format=source_format,
            operating_point=operating_point,
            study_commit=study_commit,
            time_index=time_index,
            scenario_id=scenario_id,
            edits=edits,
            to_balanced=to_balanced,
            base_mva=base_mva,
        )
        conv = prepared.emit("egret-json")
        path, info = _stage_egret_model(conv.text)
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "case_file": path,
        "model_info": info,
        **prepared.response_fields(conv),
    }


@mcp.tool()
def load_model_from_json(
    network_json: str = "",
    operating_point: Optional[int] = None,
    study_commit: Optional[int] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    powerio_ir: str = "",
    edits: str = "",
    to_balanced: bool = False,
    base_mva: float = 100.0,
) -> Dict[str, Any]:
    """Convert a selected PowerIO IR module into an Egret model.

    Accepts the `json` string returned by the powerio server's parse tool,
    so a case parsed once there feeds egret without re-reading the file.
    Converts it to egret JSON, validates it as an egret
    ModelData, and stages it to a temp file. Pass the returned `case_file`
    path to the solver tools. powerio is a core dependency, so this is always
    available.

    Args:
        network_json: The JSON transport string from powerio
        operating_point: Compatibility alias for time_index
        study_commit: Retired package selector; export a Tellegen Study state as IR
        time_index: Explicit TimeSeries index
        scenario_id: Explicit ScenarioSet identifier
        powerio_ir: Serialized PowerIO IR from the powerio server (the
            preferred spelling; network_json is its alias)
        edits: JSON list of typed what-if edits PowerIO applies before the
            conversion, in list order, for example
            [{"op": "set_load_active_power", "load": "loads:0", "mw": 91.5}]
            Consecutive updates of one class apply as one atomic batch, and a
            bus load reallocation sees the values the edits before it produced.
        to_balanced: Authorize the multiconductor to balanced transformation;
            the response carries its readiness report as `lowering`
        base_mva: System base for that transformation

    Returns:
        Dict with status, the staged `case_file` path, model element counts,
        and powerio's fidelity warnings
    """
    try:
        prepared = resolve_solver_case(
            network_json=network_json,
            operating_point=operating_point,
            study_commit=study_commit,
            time_index=time_index,
            scenario_id=scenario_id,
            powerio_ir=powerio_ir,
            edits=edits,
            to_balanced=to_balanced,
            base_mva=base_mva,
        )
        conv = prepared.emit("egret-json")
        path, info = _stage_egret_model(conv.text)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "case_file": path,
        "model_info": info,
        **prepared.response_fields(conv),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
