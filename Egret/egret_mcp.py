import sys
import os
from mcp.server.fastmcp import FastMCP
from egret.data.model_data import ModelData
from egret.models.unit_commitment import solve_unit_commitment
from egret.models.acopf import solve_acopf, create_psv_acopf_model
from egret.models.dcopf import solve_dcopf, create_ptdf_dcopf_model
from typing import Dict, Any, Optional
import io
import logging
from contextlib import redirect_stdout, redirect_stderr
import numpy as np

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
# powerio bridge: ingest any powerio readable case into egret.
# powerio converts MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels
# JSON, or its own JSON transport to egret JSON; the staged file feeds the
# solver tools above, which only accept case_file paths. powerio is an
# optional extra, so the tools degrade to a status dict when it is missing.
# ---------------------------------------------------------------------------

_POWERIO_HINT = "powerio not installed: pip install 'powerio[mcp,matrix]'"


def _stage_egret_model(egret_json_text: str):
    """Validate egret JSON by constructing a ModelData from the parsed dict,
    stage it to a temp file the solver tools can read, and summarize it."""
    import json
    import tempfile

    md = ModelData(json.loads(egret_json_text))
    fd, path = tempfile.mkstemp(suffix=".json", prefix="egret_case_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(egret_json_text)
    info = {name: len(items) for name, items in md.data.get("elements", {}).items()}
    return path, info


@mcp.tool()
def load_model_from_any(file_path: str, source_format: Optional[str] = None) -> Dict[str, Any]:
    """Convert any powerio readable case file into an egret model.

    Reads MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels JSON, or
    egret JSON via powerio, converts it to egret JSON, validates it as an
    egret ModelData, and stages it to a temp file. Pass the returned
    `case_file` path to solve_ac_opf, solve_dc_opf, or
    solve_unit_commitment_problem. powerio is a core dependency, so this is
    always available.

    Args:
        file_path: Path to the case file
        source_format: Input format name (matpower, powermodels-json,
            egret-json, psse, powerworld); inferred from the file extension
            when omitted

    Returns:
        Dict with status, the staged `case_file` path, model element counts,
        and powerio's fidelity warnings
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        conv = powerio.convert_file(file_path, "egret-json", source_format)
        path, info = _stage_egret_model(conv.text)
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "case_file": path,
        "model_info": info,
        "warnings": list(conv.warnings),
    }


@mcp.tool()
def load_model_from_json(network_json: str) -> Dict[str, Any]:
    """Convert a powerio JSON transport string into an egret model.

    Accepts the `json` string returned by the powerio server's parse tool,
    so a case parsed once there feeds egret without re-reading the file.
    Converts it to egret JSON, validates it as an egret
    ModelData, and stages it to a temp file. Pass the returned `case_file`
    path to the solver tools. powerio is a core dependency, so this is always
    available.

    Args:
        network_json: The JSON transport string from powerio

    Returns:
        Dict with status, the staged `case_file` path, model element counts,
        and powerio's fidelity warnings
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.from_json(network_json)
        conv = case.to_format("egret-json")
        path, info = _stage_egret_model(conv.text)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "case_file": path,
        "model_info": info,
        "warnings": list(conv.warnings),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
