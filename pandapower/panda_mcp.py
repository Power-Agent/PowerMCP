from typing import Dict, List, Optional, Tuple, Any, Union
import sys
from pathlib import Path

import pandapower as pp
from mcp.server.mcpserver import MCPServer as FastMCP
import logging

# Only the repo root would shadow the real pandapower library, not this dir.
_server_dir = str(Path(__file__).resolve().parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)
from audit import audit_network as _audit_network
from operating_point import validate_operating_point as _validate_operating_point

_repo_root = str(Path(__file__).resolve().parents[1])
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.solver_case import resolve_solver_case, diagnostic_messages, diagnostic_records
    from powermcp.sandbox import PathNotAllowed, checked_path
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server with logging
logger.info("Initializing Pandapower Analysis Server")
mcp = FastMCP("Pandapower Analysis Server")

# Global variable to store the current network
_current_net = None

def _get_network() -> pp.pandapowerNet:
    """Get the current pandapower network instance.
    
    Returns:
        pp.pandapowerNet: The current network or raises error if none loaded
    """
    global _current_net
    
    if _current_net is None:
        raise RuntimeError("No pandapower network is currently loaded. Please create or load a network first.")
    return _current_net


@mcp.tool()
def audit_network() -> Dict[str, Any]:
    """Run a deterministic structural audit on the current network.

    The audit does not run a power flow and does not mutate the network.

    Returns:
        Dict whose ``status`` is ``success`` when the audit ran, or ``error``
        with a ``message`` when it could not run, like the other tools. On
        success, ``audit_status`` is the verdict (``ok``, ``warning`` or
        ``error``), ``counts`` has keys ``errors``, ``warnings`` and ``info``,
        and each of ``findings`` has ``severity``, ``code``, ``message``,
        ``element`` and ``index``.
    """
    logger.info("Auditing current pandapower network")
    try:
        report = _audit_network(_get_network()).to_dict()
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Network audit failed: {str(e)}"}
    return {
        "status": "success",
        "audit_status": report["status"],
        "counts": report["counts"],
        "findings": report["findings"],
    }


@mcp.tool()
def create_empty_network() -> Dict[str, Any]:
    """Create an empty pandapower network.
    
    Returns:
        Dict containing status and network information
    """
    logger.info("Creating an empty pandapower network")
    global _current_net
    try:
        _current_net = pp.create_empty_network()
        return {
            "status": "success",
            "message": "Empty network created successfully",
            "network_info": {
                "buses": len(_current_net.bus),
                "lines": len(_current_net.line),
                "trafos": len(_current_net.trafo)
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create empty network: {str(e)}"
        }

@mcp.tool()
def load_network(file_path: str) -> Dict[str, Any]:
    """Load a pandapower network from a JSON file.
    
    Args:
        file_path: Path to the network file (.json)
        
    Returns:
        Dict containing status and network information
    """
    try:
        file_path = checked_path(file_path, purpose="file_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    logger.info(f"Loading network from file: {file_path}")
    global _current_net
    try:
        if file_path.endswith('.json'):
            _current_net = pp.from_json(file_path)
        else:
            raise ValueError("Unsupported file format. Use a .json file.")
            
        return {
            "status": "success",
            "message": f"Network loaded successfully from {file_path}",
            "network_info": {
                "buses": len(_current_net.bus),
                "lines": len(_current_net.line),
                "trafos": len(_current_net.trafo)
            }
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"File not found: {file_path}"
        }
    except ValueError as ve:
        return {
            "status": "error",
            "message": str(ve)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load network: {str(e)}"
        }

@mcp.tool()
def run_power_flow(algorithm: str = 'nr', calculate_voltage_angles: bool = True, 
                  max_iteration: int = 10, tolerance_mva: float = 1e-8) -> Dict[str, Any]:
    """Run power flow analysis on the current network.
    
    Args:
        algorithm: Power flow algorithm ('nr' for Newton-Raphson, 'bfsw' for backward/forward sweep)
        calculate_voltage_angles: Consider voltage angles in calculation
        max_iteration: Maximum number of iterations
        tolerance_mva: Convergence tolerance in MVA
        
    Returns:
        Dict containing power flow results
    """
    logger.info("Running power flow analysis")
    try:
        net = _get_network()
        pp.runpp(net, algorithm=algorithm, calculate_voltage_angles=calculate_voltage_angles,
                max_iteration=max_iteration, tolerance_mva=tolerance_mva)
        
        # Extract key results
        results = {
            "bus_results": net.res_bus.to_dict(),
            "line_results": net.res_line.to_dict(),
            "trafo_results": net.res_trafo.to_dict(),
            "converged": net.converged
        }
        
        return {
            "status": "success",
            "message": "Power flow calculation completed successfully" if net.converged else "Power flow did not converge",
            "results": results
        }
    except RuntimeError as re:
        return {
            "status": "error",
            "message": str(re)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Power flow calculation failed: {str(e)}"
        }

@mcp.tool()
def validate_operating_point(
    voltage_min_pu: float = 0.95,
    voltage_max_pu: float = 1.05,
    line_loading_limit_percent: float = 100.0,
    trafo_loading_limit_percent: float = 100.0,
) -> Dict[str, Any]:
    """Validate the current converged operating point against voltage and loading limits.

    Reads the results of the last power flow (res_bus, res_line, res_trafo,
    res_trafo3w); it does not run a solver or modify the network, so call
    run_power_flow first. The limits are the global values passed here;
    per-element limits stored in the network (bus min_vm_pu/max_vm_pu, line
    max_loading_percent) are ignored. trafo_loading_limit_percent applies to
    2- and 3-winding transformers, and out-of-service buses are skipped.

    Args:
        voltage_min_pu: Lowest acceptable bus voltage magnitude in p.u.
        voltage_max_pu: Highest acceptable bus voltage magnitude in p.u.
        line_loading_limit_percent: Line loading limit in percent
        trafo_loading_limit_percent: Transformer loading limit in percent

    Returns:
        Dict whose ``status`` is ``success`` when the validation ran, or
        ``error`` with a ``message`` when it could not (no network, no
        converged power flow, invalid limits), like the other tools. On
        success, ``validation_status`` is the verdict:
        ``ok`` - nothing within 5% of a limit;
        ``warning`` - no violations, but an element is within 5% of a limit
            (see near_limit_codes);
        ``error`` - limit violations were found (see violations).
        A completed validation also carries criteria, summary,
        near_limit_codes, violations and counts.
    """
    try:
        net = _get_network()
        report = _validate_operating_point(
            net,
            voltage_min_pu=voltage_min_pu,
            voltage_max_pu=voltage_max_pu,
            line_loading_limit_percent=line_loading_limit_percent,
            trafo_loading_limit_percent=trafo_loading_limit_percent,
        )
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc)}
    # The validator reports "failed" when it could not run; every other
    # status is its verdict on a completed validation.
    verdict = report.pop("status")
    if verdict == "failed":
        return {"status": "error", **report}
    return {"status": "success", "validation_status": verdict, **report}

@mcp.tool()
def run_contingency_analysis(contingency_type: str = "N-1", 
                           elements: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run contingency analysis on the current network.
    
    Args:
        contingency_type: Type of contingency analysis ("N-1" or "N-2")
        elements: List of specific elements to analyze (optional)
        
    Returns:
        Dict containing contingency analysis results
    """
    logger.info("Running contingency analysis")
    try:
        net = _get_network()
        
        # Store original state
        orig_net = net.deepcopy()
        results = []
        
        # Define elements to analyze
        if elements is None:
            elements = ['line', 'trafo']
            
        # Perform contingency analysis
        for element_type in elements:
            for idx in net[element_type].index:
                # Create contingency by taking element out of service
                contingency_net = orig_net.deepcopy()
                contingency_net[element_type].at[idx, 'in_service'] = False
                
                try:
                    pp.runpp(contingency_net)
                    
                    # Check for violations
                    violations = {
                        'voltage_violations': contingency_net.res_bus[
                            (contingency_net.res_bus.vm_pu < 0.95) | 
                            (contingency_net.res_bus.vm_pu > 1.05)
                        ].index.tolist(),
                        'loading_violations': contingency_net.res_line[
                            contingency_net.res_line.loading_percent > 100
                        ].index.tolist()
                    }
                    
                    results.append({
                        'contingency': f"{element_type}_{idx}",
                        'converged': contingency_net.converged,
                        'violations': violations
                    })
                    
                except Exception as e:
                    results.append({
                        'contingency': f"{element_type}_{idx}",
                        'converged': False,
                        'error': str(e)
                    })
        
        return {
            "status": "success",
            "message": "Contingency analysis completed",
            "results": results
        }
    except RuntimeError as re:
        return {
            "status": "error",
            "message": str(re)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Contingency analysis failed: {str(e)}"
        }

@mcp.tool()
def get_network_info() -> Dict[str, Any]:
    """Get information about the current network.
    
    Returns:
        Dict containing network statistics and information
    """
    logger.info("Retrieving network information")
    try:
        net = _get_network()
        info = {
            "buses": len(net.bus),
            "lines": len(net.line),
            "trafos": len(net.trafo),
            "generators": len(net.gen),
            "loads": len(net.load),
            "switches": len(net.switch),
            "bus_data": net.bus.to_dict(),
            "line_data": net.line.to_dict(),
            "trafo_data": net.trafo.to_dict()
        }
        
        return {
            "status": "success",
            "message": "Network information retrieved successfully",
            "info": info
        }
    except RuntimeError as re:
        return {
            "status": "error",
            "message": str(re)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get network information: {str(e)}"
        }

# ---------------------------------------------------------------------------
# PowerIO interchange: resolve one balanced state and use PowerIO's native
# pandapower writer. Export still round-trips pandapower's PYPOWER tables
# through PowerIO because pandapower has no corresponding native writer.
# ---------------------------------------------------------------------------

_POWERIO_HINT = "powerio not installed: pip install 'powerio[mcp,matrix]'"

def _powerio_to_net(case):
    """Use PowerIO's native writer to create the pandapower network.

    Returns the network and the shared response fields: value type, selection,
    diagnostics, warnings, emission fidelity, edits, and lowering report.
    """
    conversion = case.emit("pandapower-json")
    return pp.from_json_string(conversion.text), case.response_fields(conversion)


def _network_info_response(message: str, **fields: Any) -> Dict[str, Any]:
    """A success response carrying the loaded network's counts and every field.

    ``fields`` is the shared tail ``SolverCase.response_fields`` builds, so
    every key it states, including an empty ``warnings`` or ``diagnostics``
    list, reaches the caller unchanged.
    """
    response = {
        "status": "success",
        "message": message,
        "network_info": {
            "buses": len(_current_net.bus),
            "lines": len(_current_net.line),
            "trafos": len(_current_net.trafo),
        },
    }
    response.update(fields)
    return response


@mcp.tool()
def load_network_from_any(
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
    """Load a network from any powerio readable case file.

    Reads any balanced PowerIO format or a ``.pio.json`` module and replaces
    the current network. Select a TimeSeries with time_index and a ScenarioSet with scenario_id.
    The selected typed value is validated before conversion.

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
        Dict containing status and network information
    """
    try:
        file_path = checked_path(file_path, purpose="file_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    logger.info(f"Loading network via powerio from: {file_path}")
    global _current_net
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
        _current_net, fields = _powerio_to_net(prepared)
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}
    return _network_info_response(
        f"Network loaded successfully from {file_path}",
        **fields,
    )


@mcp.tool()
def load_network_from_json(
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
    """Load PowerIO model JSON or one selected ``.pio.json`` module state.

    Accepts the `json` string returned by the powerio server's parse tool,
    so a case parsed once there loads here without passing a file around or
    re-parsing it. Expects source-valued tables (MW, degrees)
    as parse emits them, not the per-unit normalize form. Replaces
    the currently loaded network. powerio is a core dependency, so this is
    always available.

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
        Dict containing status and network information
    """
    logger.info("Loading network from powerio JSON transport")
    global _current_net
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
        _current_net, fields = _powerio_to_net(prepared)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}
    return _network_info_response(
        "Network loaded successfully from PowerIO IR",
        **fields,
    )


@mcp.tool()
def export_network_to_format(to_format: str) -> Dict[str, Any]:
    """Export the current network to a power system case format via powerio.

    Converts the loaded network to MATPOWER tables and serializes them with
    powerio. to_format is a powerio format name: matpower (m),
    powermodels-json (pm), egret-json (egret), psse (raw), powerworld (aux).
    powerio is a core dependency, so this is always available.

    Args:
        to_format: Target format name

    Returns:
        Dict with status, the exported case `text`, and fidelity `warnings`
        listing anything the target format could not represent
    """
    logger.info(f"Exporting network via powerio to format: {to_format}")
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        net = _get_network()
        from pandapower.converter.pypower.to_ppc import to_ppc

        ppc = to_ppc(net, init="flat")
        module = powerio.PioModule.from_value(powerio.from_ppc(ppc))
        conv = powerio.emit(module, to_format)
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to export network: {str(e)}"}
    if conv.text is None:
        return {
            "status": "error",
            "message": f"{to_format} is a directory format; use the powerio server's emit tool with a destination",
        }
    return {
        "status": "success",
        "text": conv.text,
        "fidelity": conv.fidelity,
        "diagnostics": diagnostic_records(conv.diagnostics),
        "warnings": list(diagnostic_messages(conv.diagnostics)),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")