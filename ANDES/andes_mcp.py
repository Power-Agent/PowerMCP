import andes
import logging
import os
import io
import sys
import shutil
import json
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional

# Storage directory resolved lazily (no filesystem writes at import time)
def _andes_runs_dir():
    try:
        from powermcp.paths import runs_dir
        return str(runs_dir("andes"))
    except Exception:
        import os
        d = os.path.join(os.path.expanduser("~"), ".powermcp", "runs", "andes")
        os.makedirs(d, exist_ok=True)
        return d

# Configure logging (stream only at import; file handler attached lazily)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Configure ANDES logging
andes.config_logger(stream_level=50)  # 50 is CRITICAL level
logging.getLogger('andes').setLevel(logging.WARNING)
logging.getLogger('numpy').setLevel(logging.WARNING)
logging.getLogger('scipy').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Attach a file handler lazily on first tool use (no log file opened at import)
_file_handler_added = False

def _ensure_file_logging():
    global _file_handler_added
    if _file_handler_added:
        return
    try:
        fh = logging.FileHandler(os.path.join(_andes_runs_dir(), 'mcp_server.log'))
        fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(fh)
    except Exception:
        pass
    _file_handler_added = True

# Initialize MCP server
mcp = FastMCP("ANDES MCP Server")

# Initialize system state
system_state: Dict[str, Any] = {}

@mcp.tool()
def run_power_flow(file_path: str) -> Dict[str, Any]:
    """Run power flow analysis on a power system case
    
    Args:
        file_path: Path to the case file
    
    Returns:
        Dict containing power flow results and output information
    """
    try:
        _ensure_file_logging()
        # Convert to absolute path if not already
        abs_file_path = os.path.abspath(file_path)
        if not os.path.exists(abs_file_path):
            return {
                "status": "error",
                "message": f"Input file not found: {abs_file_path}"
            }

        # Create a unique directory for this run
        run_dir = os.path.join(_andes_runs_dir(), f"pf_{Path(abs_file_path).stem}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Copy input file to run directory
        input_file = os.path.join(run_dir, os.path.basename(abs_file_path))
        shutil.copy2(abs_file_path, input_file)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Run power flow with minimal output
                ss = andes.run(input_file, no_output=True, verbose=50)
                
                # Store system state for other tools
                system_state['current_system'] = ss
                
                # Extract key power flow results
                pflow_results = {
                    "converged": ss.PFlow.converged,
                    "iterations": ss.PFlow.niter if hasattr(ss.PFlow, 'niter') else 0,
                    "max_mis": float(ss.PFlow.mis[-1]) if hasattr(ss.PFlow, 'mis') and len(ss.PFlow.mis) > 0 else 0.0,
                    "time": float(ss.PFlow.t) if hasattr(ss.PFlow, 't') else 0.0
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Power flow completed successfully" if ss.PFlow.converged else "Power flow did not converge",
                    "power_flow": pflow_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in power flow analysis: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def run_time_domain_simulation(step_size: float = 0.01, t_end: float = 10.0) -> Dict[str, Any]:
    """Run time domain simulation on the currently loaded power system
    
    Args:
        step_size: Time step size in seconds
        t_end: End time in seconds
    
    Returns:
        Dict containing simulation results and output information
    """
    try:
        _ensure_file_logging()
        if 'current_system' not in system_state:
            return {
                "status": "error",
                "message": "No power system currently loaded. Run power flow first."
            }

        ss = system_state['current_system']

        # Create a unique directory for this run
        run_dir = os.path.join(_andes_runs_dir(), f"tds_{int(t_end)}s")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Configure time domain simulation parameters
                ss.TDS.config.tf = t_end
                ss.TDS.config.tstep = step_size
                
                # Run time domain simulation
                ss.TDS.init()
                success = ss.TDS.run()
                
                # Extract key simulation results
                tds_results = {
                    "t_array": ss.dae.t.tolist() if hasattr(ss.dae, 't') else [],
                    "step_size": float(ss.TDS.config.tstep),
                    "t_end": float(ss.TDS.config.tf),
                    "success": success,
                    "status": "completed" if success else "failed"
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Time domain simulation completed successfully" if success else "Time domain simulation failed",
                    "simulation": tds_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in time domain simulation: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def run_eigenvalue_analysis(file_path: str) -> Dict[str, Any]:
    """Run eigenvalue analysis on a power system case
    
    Args:
        file_path: Path to the case file
    
    Returns:
        Dict containing the eigenvalue analysis results
    """
    try:
        _ensure_file_logging()
        # Convert to absolute path if relative
        abs_file_path = os.path.abspath(file_path)

        if not os.path.exists(abs_file_path):
            return {
                "status": "error",
                "message": f"File not found: {file_path}"
            }

        # Create a unique directory for this run
        run_dir = os.path.join(_andes_runs_dir(), f"eig_{Path(abs_file_path).stem}")
        os.makedirs(run_dir, exist_ok=True)
        
        # Save current directory and change to run directory
        original_dir = os.getcwd()
        os.chdir(run_dir)
        
        try:
            # Capture stdout/stderr
            f_out = io.StringIO()
            f_err = io.StringIO()
            
            with redirect_stdout(f_out), redirect_stderr(f_err):
                # Load the system
                ss = andes.run(abs_file_path, no_output=True)
                system_state['current_system'] = ss
                
                # Run eigenvalue analysis
                success = ss.EIG.run()
                
                # Extract eigenvalue results
                eig_results = {
                    "n_eigenvalues": len(ss.EIG.mu) if hasattr(ss.EIG, 'mu') else 0,
                    "eigenvalues": ss.EIG.mu.tolist() if hasattr(ss.EIG, 'mu') else [],
                    "eigenvectors": ss.EIG.vectors.tolist() if hasattr(ss.EIG, 'vectors') else [],
                    "participation_factors": ss.EIG.pfactors.tolist() if hasattr(ss.EIG, 'pfactors') else [],
                    "state_variables": ss.EIG.state_desc if hasattr(ss.EIG, 'state_desc') else [],
                    "success": success
                }
                
                # Get list of output files
                output_files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
                
                result = {
                    "status": "success",
                    "message": "Eigenvalue analysis completed successfully" if success else "Eigenvalue analysis failed",
                    "analysis": eig_results,
                    "output_dir": run_dir,
                    "output_files": output_files,
                    "stdout": f_out.getvalue(),
                    "stderr": f_err.getvalue()
                }
                
                return result
                
        finally:
            # Always change back to original directory
            os.chdir(original_dir)
            
    except Exception as e:
        logger.error(f"Error in eigenvalue analysis: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@mcp.tool()
def get_system_info() -> Dict[str, Any]:
    """
    Get information about the currently loaded power system
    
    Returns:
        Dict containing system information
    """
    if 'current_system' not in system_state:
        return {
            "status": "error",
            "message": "No power system currently loaded"
        }
    
    try:
        # Capture stdout/stderr
        f_out = io.StringIO()
        f_err = io.StringIO()
        
        with redirect_stdout(f_out), redirect_stderr(f_err):
            ss = system_state['current_system']
            info = {
                "status": "success",
                "num_buses": len(ss.Bus.idx.v) if hasattr(ss.Bus, 'idx') else 0,
                "num_generators": (len(ss.PV.idx.v) if hasattr(ss.PV, 'idx') else 0) + 
                                (len(ss.GENROU.idx.v) if hasattr(ss.GENROU, 'idx') else 0),
                "system_name": ss.name if hasattr(ss, 'name') else "Unknown",
                "base_mva": float(ss.config.mva) if hasattr(ss.config, 'mva') else 100.0,
                "stdout": f_out.getvalue(),
                "stderr": f_err.getvalue()
            }
        
        return info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------------------------
# powerio bridge: load any powerio readable case into ANDES.
# powerio parses MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels
# JSON, and egret JSON; the case is staged as a MATPOWER file that ANDES loads
# natively via run_power_flow. powerio is an optional extra, so the tools
# degrade gracefully when it is missing.
# ---------------------------------------------------------------------------

_POWERIO_HINT = "powerio not installed: pip install 'powerio[mcp,matrix]'"


@mcp.tool()
def load_network_from_json(
    network_json: str,
    out_path: str,
) -> Dict[str, Any]:
    """Stage a powerio JSON transport string as a MATPOWER file for ANDES.

    Accepts the ``json`` string returned by the powerio server's parse_case or
    case_to_json tools. Converts the network to MATPOWER format, writes it to
    out_path (use a .m extension), and returns the path along with component
    counts. Pass out_path to run_power_flow to run the simulation. Requires the
    powerio extra (pip install 'powermcp[powerio]').

    Args:
        network_json: The JSON transport string from powerio
        out_path: Destination for the MATPOWER case file (.m)

    Returns:
        Dict with status, case_file path, component counts, and fidelity warnings
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.from_json(network_json)
        conv = case.to_format("matpower")
        abs_out = os.path.abspath(out_path)
        with open(abs_out, "w") as fh:
            fh.write(conv.text)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "message": f"Case staged at {abs_out}; pass this path to run_power_flow",
        "case_file": abs_out,
        "info": {
            "buses": case.n_buses,
            "branches": case.n_branches,
            "generators": case.n_gens,
        },
        "warnings": list(conv.warnings),
    }


@mcp.tool()
def load_network_from_any(
    file_path: str,
    out_path: str,
    source_format: Optional[str] = None,
) -> Dict[str, Any]:
    """Stage any powerio readable case as a MATPOWER file for ANDES.

    Reads MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels JSON, or
    egret JSON via powerio and writes a MATPOWER file to out_path (use a .m
    extension). Pass out_path to run_power_flow to run the simulation. Requires
    the powerio extra (pip install 'powermcp[powerio]').

    Args:
        file_path: Path to the source case file
        out_path: Destination for the MATPOWER case file (.m)
        source_format: Input format name (matpower, powermodels-json, egret-json,
            psse, powerworld); inferred from the file extension when omitted

    Returns:
        Dict with status, case_file path, component counts, and fidelity warnings
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.parse_file(file_path, source_format)
        conv = case.to_format("matpower")
        abs_out = os.path.abspath(out_path)
        with open(abs_out, "w") as fh:
            fh.write(conv.text)
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "message": f"Case staged at {abs_out}; pass this path to run_power_flow",
        "case_file": abs_out,
        "info": {
            "buses": case.n_buses,
            "branches": case.n_branches,
            "generators": case.n_gens,
        },
        "warnings": list(conv.warnings),
    }


if __name__ == "__main__":
    print(f"Starting ANDES MCP Server")
    print(f"Using storage directory: {_andes_runs_dir()}")
    mcp.run(transport="stdio")