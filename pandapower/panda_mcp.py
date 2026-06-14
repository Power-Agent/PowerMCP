from typing import Dict, List, Optional, Tuple, Any, Union
import pandapower as pp
from mcp.server.fastmcp import FastMCP
import logging


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
    """Load a pandapower network from a file.
    
    Args:
        file_path: Path to the network file (.json, .p)
        
    Returns:
        Dict containing status and network information
    """
    logger.info(f"Loading network from file: {file_path}")
    global _current_net
    try:
        if file_path.endswith('.json'):
            _current_net = pp.from_json(file_path)
        elif file_path.endswith('.p'):
            _current_net = pp.from_pickle(file_path)
        else:
            raise ValueError("Unsupported file format. Use .json or .p files.")
            
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
# powerio bridge: exchange cases with the powerio conversion server.
# Its parse_case / case_to_json tools emit a JSON transport string that
# load_network_from_json ingests directly, so a case parsed once there loads
# here without re-reading the file; export_network_to_format sends the current
# network back out through powerio. powerio is an optional extra, so each tool
# degrades to a status dict when it is missing.
# ---------------------------------------------------------------------------

_POWERIO_HINT = "powerio not installed: pip install 'powerio[mcp,matrix]'"

# powerio bus kind -> MATPOWER/PYPOWER BUS_TYPE code
# NOTE: _PPC_BUS_TYPE and _powerio_case_to_ppc are duplicated between
# pandapower/panda_mcp.py and PyPSA/pypsa_mcp.py (server scripts are
# standalone); keep the two copies identical and sync any fix to both.
_PPC_BUS_TYPE = {"PQ": 1.0, "PV": 2.0, "REF": 3.0, "ISOLATED": 4.0}


def _powerio_case_to_ppc(case) -> Dict[str, Any]:
    """Build a PYPOWER ppc dict from a powerio Network.

    Values are MATPOWER style (MW, MVAr, degrees), which is what powerio's
    parsed source tables carry; in-service loads and shunts are summed into
    the bus table the way MATPOWER stores them.
    """
    import numpy as np

    buses = case.buses
    row_of = {b["id"]: i for i, b in enumerate(buses)}
    bus = np.zeros((len(buses), 13))
    for i, b in enumerate(buses):
        bus[i, :] = (
            b["id"], _PPC_BUS_TYPE.get(b["kind"], 1.0), 0.0, 0.0, 0.0, 0.0,
            b["area"], b["vm"], b["va"], b["base_kv"], b["zone"], b["vmax"], b["vmin"],
        )
    for load in case.loads:
        i = row_of.get(load["bus"])
        if i is not None and load["in_service"]:
            bus[i, 2] += load["p"]
            bus[i, 3] += load["q"]
    for shunt in case.shunts:
        i = row_of.get(shunt["bus"])
        if i is not None and shunt["in_service"]:
            bus[i, 4] += shunt["g"]
            bus[i, 5] += shunt["b"]

    gens = case.generators
    gen = np.zeros((len(gens), 21))
    for i, g in enumerate(gens):
        gen[i, :10] = (
            g["bus"], g["pg"], g["qg"], g["qmax"], g["qmin"], g["vg"],
            g["mbase"], float(g["in_service"]), g["pmax"], g["pmin"],
        )

    branches = case.branches
    branch = np.zeros((len(branches), 13))
    for i, br in enumerate(branches):
        branch[i, :] = (
            br["from_id"], br["to_id"], br["r"], br["x"], br["b"],
            br["rate_a"], br["rate_b"], br["rate_c"], br["tap"], br["shift"],
            float(br["in_service"]), br["angmin"], br["angmax"],
        )

    ppc = {
        "version": "2",
        "baseMVA": float(case.base_mva),
        "bus": bus,
        "gen": gen,
        "branch": branch,
    }

    # gencost rows are [model, startup, shutdown, ncost, coeffs...] with
    # coefficients left-aligned after ncost, padded to the widest row — the
    # layout from_ppc reads. MATPOWER requires cost data for all gens or none,
    # so a partial cost set is dropped rather than padded with fake rows.
    costs = [g["cost"] for g in gens]
    if costs and all(c is not None for c in costs):
        gencost = np.zeros((len(costs), 4 + max(len(c["coeffs"]) for c in costs)))
        for i, c in enumerate(costs):
            gencost[i, :4] = (c["model"], c["startup"], c["shutdown"], c["ncost"])
            gencost[i, 4:4 + len(c["coeffs"])] = c["coeffs"]
        ppc["gencost"] = gencost
    return ppc


def _ppc_to_net(ppc) -> pp.pandapowerNet:
    from pandapower.converter.pypower.from_ppc import from_ppc

    return from_ppc(ppc)


def _ppc_to_matpower_text(ppc) -> str:
    """Serialize PYPOWER input tables as MATPOWER .m text for powerio to parse.
    Columns beyond the MATPOWER input widths (result columns) are dropped."""
    width = {"bus": 13, "gen": 21, "branch": 13}
    out = [
        "function mpc = ppc_export",
        "mpc.version = '2';",
        f"mpc.baseMVA = {float(ppc['baseMVA'])!r};",
    ]
    for name in ("bus", "gen", "branch", "gencost"):
        table = ppc.get(name)
        if table is None or len(table) == 0:
            continue
        w = width.get(name)
        rows = "\n".join(
            "\t" + "\t".join(repr(float(v)) for v in (row[:w] if w else row)) + ";"
            for row in table
        )
        out.append(f"mpc.{name} = [\n{rows}\n];")
    return "\n".join(out) + "\n"


def _network_info_response(message: str) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "network_info": {
            "buses": len(_current_net.bus),
            "lines": len(_current_net.line),
            "trafos": len(_current_net.trafo),
        },
    }


@mcp.tool()
def load_network_from_any(file_path: str, source_format: Optional[str] = None) -> Dict[str, Any]:
    """Load a network from any powerio readable case file.

    Reads MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels JSON, or
    egret JSON via powerio and converts it to a pandapower network, replacing
    the currently loaded one. Use this for case formats load_network does not
    accept. powerio is a core dependency, so this is always available.

    Args:
        file_path: Path to the case file
        source_format: Input format name (matpower, powermodels-json,
            egret-json, psse, powerworld); inferred from the file extension
            when omitted

    Returns:
        Dict containing status and network information
    """
    logger.info(f"Loading network via powerio from: {file_path}")
    global _current_net
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.parse_file(file_path, source_format)
        _current_net = _ppc_to_net(_powerio_case_to_ppc(case))
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}
    return _network_info_response(f"Network loaded successfully from {file_path}")


@mcp.tool()
def load_network_from_json(network_json: str) -> Dict[str, Any]:
    """Load a network from a powerio JSON transport string.

    Accepts the `json` string returned by the powerio server's parse_case or
    case_to_json tools, so a case parsed once there loads here without passing
    a file around or re-parsing it. Expects source-valued tables (MW, degrees)
    as parse_case emits them, not the per-unit normalize_case form. Replaces
    the currently loaded network. powerio is a core dependency, so this is
    always available.

    Args:
        network_json: The JSON transport string from powerio

    Returns:
        Dict containing status and network information
    """
    logger.info("Loading network from powerio JSON transport")
    global _current_net
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.from_json(network_json)
        _current_net = _ppc_to_net(_powerio_case_to_ppc(case))
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}
    return _network_info_response("Network loaded successfully from JSON transport")


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
        case = powerio.parse_str(_ppc_to_matpower_text(ppc), "matpower")
        conv = case.to_format(to_format)
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to export network: {str(e)}"}
    return {"status": "success", "text": conv.text, "warnings": list(conv.warnings)}


if __name__ == "__main__":
    mcp.run(transport="stdio")