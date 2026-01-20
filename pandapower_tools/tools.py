"""
PowerMCP Pandapower Module
Provides power system analysis tools using pandapower.
"""

from typing import Dict, List, Optional, Any
import json
import inspect
import copy

try:
    import pandapower as pp
    import pandapower.networks as pp_networks
    PANDAPOWER_AVAILABLE = True
except ImportError:
    PANDAPOWER_AVAILABLE = False
    pp = None
    pp_networks = None

# Global variable to store the current network
_current_net = None


def _get_available_networks() -> Dict[str, Any]:
    """Dynamically discover all available network functions in pandapower.networks.
    
    Returns:
        Dict mapping network names to their callable functions
    """
    if not PANDAPOWER_AVAILABLE:
        return {}
    
    network_functions = {}
    
    # Get all members of pp.networks module
    for name, obj in inspect.getmembers(pp_networks):
        # Skip private/internal items
        if name.startswith('_'):
            continue
        
        # Check if it's a callable (function) that could create a network
        if callable(obj):
            # Try to determine if this function creates a network
            # Most network functions either:
            # 1. Start with 'case' (IEEE cases)
            # 2. Start with 'create_' (CIGRE networks, etc.)
            # 3. Are known network names (iceland, GBnetwork, etc.)
            # 4. Return a pandapower network
            
            # Get function signature to check if it can be called with no required args
            try:
                sig = inspect.signature(obj)
                # Check if all parameters have defaults (can be called without args)
                can_call_without_args = all(
                    p.default != inspect.Parameter.empty 
                    for p in sig.parameters.values()
                )
            except (ValueError, TypeError):
                can_call_without_args = False
            
            # Include functions that look like network creators
            if (name.startswith('case') or 
                name.startswith('create_') or
                name in ['iceland', 'GBnetwork', 'GBreducednetwork', 
                         'simple_four_bus_system', 'simple_mv_open_ring_net',
                         'mv_oberrhein', 'panda_four_load_branch',
                         'four_loads_with_branches_out', 'example_simple',
                         'example_multivoltage', 'kb_extrem_landnetz_trafo',
                         'kb_extrem_landnetz_freileitung', 'kb_extrem_vorstadtnetz_trafo',
                         'kb_extrem_vorstadtnetz_kabel'] or
                can_call_without_args):
                network_functions[name] = obj
    
    return network_functions


# Cache the available networks to avoid repeated inspection
_NETWORK_FUNCTIONS_CACHE = None


def _get_network_functions():
    """Get cached network functions or build cache."""
    global _NETWORK_FUNCTIONS_CACHE
    if _NETWORK_FUNCTIONS_CACHE is None:
        _NETWORK_FUNCTIONS_CACHE = _get_available_networks()
    return _NETWORK_FUNCTIONS_CACHE


def _get_network():
    """Get the current pandapower network instance."""
    global _current_net
    if _current_net is None:
        raise RuntimeError("No pandapower network is currently loaded. Please create or load a network first.")
    return _current_net


def _set_network(net):
    """Set the current pandapower network instance."""
    global _current_net
    _current_net = copy.deepcopy(net)

def create_empty_network() -> Dict[str, Any]:
    """Create an empty pandapower network.
    
    Returns:
        Dict containing status and network information
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    global _current_net
    try:
        _current_net = pp.create_empty_network()
        return {
            "status": "success",
            "message": "Empty network created successfully",
            "network_info": {
                "buses": len(_current_net.bus),
                "lines": len(_current_net.line),
                "transformers": len(_current_net.trafo),
                "generators": len(_current_net.gen),
                "loads": len(_current_net.load)
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create empty network: {str(e)}"}


def create_test_network(network_type: str = "case9") -> Dict[str, Any]:
    """Create a standard IEEE test network or other built-in pandapower network.
    
    Args:
        network_type: Type of test network. Use get_available_networks() to see all options.
                      Common examples: case4gs, case5, case6ww, case9, case14, case24_ieee_rts,
                      case30, case33bw, case39, case57, case89pegase, case118, case145, case300,
                      case1354pegase, case1888rte, case2848rte, case2869pegase, case3120sp,
                      case6470rte, case6495rte, case6515rte, case9241pegase, GBnetwork,
                      GBreducednetwork, iceland, create_cigre_network_hv, create_cigre_network_mv,
                      create_cigre_network_lv, mv_oberrhein, simple_four_bus_system,
                      simple_mv_open_ring_net, example_simple, example_multivoltage, and more.
    
    Returns:
        Dict containing status and network information
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    global _current_net
    try:
        network_functions = _get_network_functions()
        
        if network_type not in network_functions:
            # Try to find a close match (case-insensitive)
            lower_type = network_type.lower()
            for key in network_functions:
                if key.lower() == lower_type:
                    network_type = key
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Unknown network type: {network_type}",
                    "available_types": sorted(list(network_functions.keys())),
                    "hint": "Use get_available_networks() to see all available network types"
                }
        
        _current_net = network_functions[network_type]()
        
        return {
            "status": "success",
            "message": f"Created {network_type} test network",
            "network_info": {
                "buses": len(_current_net.bus),
                "lines": len(_current_net.line),
                "transformers": len(_current_net.trafo),
                "generators": len(_current_net.gen),
                "loads": len(_current_net.load),
                "ext_grids": len(_current_net.ext_grid),
                "shunts": len(_current_net.shunt) if hasattr(_current_net, 'shunt') else 0
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_available_networks() -> Dict[str, Any]:
    """Get a list of all available pandapower test networks.
    
    Returns:
        Dict containing list of available network types with descriptions
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        network_functions = _get_network_functions()
        
        # Categorize networks
        ieee_cases = []
        pegase_cases = []
        rte_cases = []
        cigre_networks = []
        other_networks = []
        
        for name in sorted(network_functions.keys()):
            if name.startswith('case') and 'pegase' in name.lower():
                pegase_cases.append(name)
            elif name.startswith('case') and 'rte' in name.lower():
                rte_cases.append(name)
            elif name.startswith('case'):
                ieee_cases.append(name)
            elif 'cigre' in name.lower():
                cigre_networks.append(name)
            else:
                other_networks.append(name)
        
        return {
            "status": "success",
            "total_networks": len(network_functions),
            "categories": {
                "ieee_cases": ieee_cases,
                "pegase_cases": pegase_cases,
                "rte_cases": rte_cases,
                "cigre_networks": cigre_networks,
                "other_networks": other_networks
            },
            "all_networks": sorted(list(network_functions.keys()))
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def load_network(file_path: str) -> Dict[str, Any]:
    """Load a pandapower network from a file.
    
    Args:
        file_path: Path to the network file (.json or .p)
        
    Returns:
        Dict containing status and network information
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    global _current_net
    try:
        if file_path.endswith('.json'):
            _current_net = pp.from_json(file_path)
        elif file_path.endswith('.p'):
            _current_net = pp.from_pickle(file_path)
        else:
            return {"status": "error", "message": "Unsupported file format. Use .json or .p files."}
            
        return {
            "status": "success",
            "message": f"Network loaded successfully from {file_path}",
            "network_info": {
                "buses": len(_current_net.bus),
                "lines": len(_current_net.line),
                "transformers": len(_current_net.trafo),
                "generators": len(_current_net.gen),
                "loads": len(_current_net.load)
            }
        }
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}


def run_power_flow(algorithm: str = "nr", calculate_voltage_angles: bool = True,
                   max_iteration: int = 50, tolerance_mva: float = 1e-8) -> Dict[str, Any]:
    """Run AC power flow analysis on the current network.
    
    Args:
        algorithm: Power flow algorithm ('nr', 'bfsw', 'gs', 'fdbx', 'fdxb')
        calculate_voltage_angles: Whether to calculate voltage angles
        max_iteration: Maximum number of iterations
        tolerance_mva: Convergence tolerance in MVA
    
    Returns:
        Dict containing power flow results
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        pp.runpp(net, algorithm=algorithm, calculate_voltage_angles=calculate_voltage_angles,
                 max_iteration=max_iteration, tolerance_mva=tolerance_mva)
        
        results = {
            "status": "success",
            "message": "Power flow converged successfully" if net.converged else "Power flow did not converge",
            "converged": net.converged,
            "bus_results": {
                "vm_pu": net.res_bus["vm_pu"].to_dict(),
                "va_degree": net.res_bus["va_degree"].to_dict(),
                "p_mw": net.res_bus["p_mw"].to_dict(),
                "q_mvar": net.res_bus["q_mvar"].to_dict()
            },
            "line_results": {
                "loading_percent": net.res_line["loading_percent"].to_dict(),
                "p_from_mw": net.res_line["p_from_mw"].to_dict(),
                "p_to_mw": net.res_line["p_to_mw"].to_dict(),
                "pl_mw": net.res_line["pl_mw"].to_dict(),
                "ql_mvar": net.res_line["ql_mvar"].to_dict()
            },
            "total_losses": {
                "p_mw": float(net.res_line["pl_mw"].sum()),
                "q_mvar": float(net.res_line["ql_mvar"].sum())
            }
        }
        
        if len(net.trafo) > 0:
            results["transformer_results"] = {
                "loading_percent": net.res_trafo["loading_percent"].to_dict()
            }
        
        return results
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Power flow calculation failed: {str(e)}"}


def run_dc_power_flow() -> Dict[str, Any]:
    """Run DC power flow analysis on the current network.
    
    Returns:
        Dict containing DC power flow results
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        pp.rundcpp(net)
        
        return {
            "status": "success",
            "message": "DC power flow completed",
            "bus_results": {
                "va_degree": net.res_bus["va_degree"].to_dict(),
                "p_mw": net.res_bus["p_mw"].to_dict()
            },
            "line_results": {
                "p_from_mw": net.res_line["p_from_mw"].to_dict(),
                "p_to_mw": net.res_line["p_to_mw"].to_dict()
            }
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"DC power flow calculation failed: {str(e)}"}


def get_network_info() -> Dict[str, Any]:
    """Get information about the current network.
    
    Returns:
        Dict containing network statistics
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        
        info = {
            "status": "success",
            "component_counts": {
                "buses": len(net.bus),
                "lines": len(net.line),
                "transformers": len(net.trafo),
                "generators": len(net.gen),
                "static_generators": len(net.sgen),
                "loads": len(net.load),
                "external_grids": len(net.ext_grid),
                "shunts": len(net.shunt) if hasattr(net, 'shunt') else 0,
                "switches": len(net.switch) if hasattr(net, 'switch') else 0
            },
            "bus_data": net.bus.to_dict() if len(net.bus) <= 50 else f"Too large ({len(net.bus)} buses)",
            "line_data": net.line.to_dict() if len(net.line) <= 50 else f"Too large ({len(net.line)} lines)",
            "load_data": net.load.to_dict() if len(net.load) <= 50 else f"Too large ({len(net.load)} loads)",
            "gen_data": net.gen.to_dict() if len(net.gen) <= 50 else f"Too large ({len(net.gen)} generators)"
        }
        
        return info
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get network information: {str(e)}"}


def add_bus(name: str, vn_kv: float, bus_type: str = "b",
            in_service: bool = True, max_vm_pu: float = 1.1,
            min_vm_pu: float = 0.9) -> Dict[str, Any]:
    """Add a bus to the current network.
    
    Args:
        name: Name of the bus
        vn_kv: Nominal voltage in kV
        bus_type: Bus type ('b' for PQ bus, 'n' for node)
        in_service: Whether bus is in service
        max_vm_pu: Maximum voltage magnitude in per unit
        min_vm_pu: Minimum voltage magnitude in per unit
    
    Returns:
        Dict with status and new bus index
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        bus_idx = pp.create_bus(net, vn_kv=vn_kv, name=name, type=bus_type,
                                in_service=in_service, max_vm_pu=max_vm_pu, min_vm_pu=min_vm_pu)
        return {
            "status": "success",
            "message": f"Bus '{name}' added successfully",
            "bus_index": int(bus_idx),
            "total_buses": len(net.bus)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_line(from_bus: int, to_bus: int, length_km: float,
             std_type: str = "NAYY 4x50 SE", name: str = "") -> Dict[str, Any]:
    """Add a line to the current network.
    
    Args:
        from_bus: Index of the starting bus
        to_bus: Index of the ending bus
        length_km: Length of the line in km
        std_type: Standard line type
        name: Name of the line
    
    Returns:
        Dict with status and new line index
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        line_idx = pp.create_line(net, from_bus=from_bus, to_bus=to_bus,
                                  length_km=length_km, std_type=std_type, name=name)
        return {
            "status": "success",
            "message": f"Line from bus {from_bus} to bus {to_bus} added",
            "line_index": int(line_idx),
            "total_lines": len(net.line)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_load(bus: int, p_mw: float, q_mvar: float = 0.0, name: str = "") -> Dict[str, Any]:
    """Add a load to the current network.
    
    Args:
        bus: Index of the bus to connect the load
        p_mw: Active power of the load in MW
        q_mvar: Reactive power of the load in Mvar
        name: Name of the load
    
    Returns:
        Dict with status and new load index
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        load_idx = pp.create_load(net, bus=bus, p_mw=p_mw, q_mvar=q_mvar, name=name)
        return {
            "status": "success",
            "message": f"Load added at bus {bus}",
            "load_index": int(load_idx),
            "total_loads": len(net.load)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_generator(bus: int, p_mw: float, vm_pu: float = 1.0,
                  name: str = "", controllable: bool = True) -> Dict[str, Any]:
    """Add a generator to the current network.
    
    Args:
        bus: Index of the bus to connect the generator
        p_mw: Active power output in MW
        vm_pu: Voltage setpoint in per unit
        name: Name of the generator
        controllable: Whether the generator is controllable
    
    Returns:
        Dict with status and new generator index
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        gen_idx = pp.create_gen(net, bus=bus, p_mw=p_mw, vm_pu=vm_pu,
                                name=name, controllable=controllable)
        return {
            "status": "success",
            "message": f"Generator added at bus {bus}",
            "generator_index": int(gen_idx),
            "total_generators": len(net.gen)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_ext_grid(bus: int, vm_pu: float = 1.0, va_degree: float = 0.0,
                 name: str = "External Grid") -> Dict[str, Any]:
    """Add an external grid (slack bus) to the current network.
    
    Args:
        bus: Index of the bus to connect the external grid
        vm_pu: Voltage magnitude setpoint in per unit
        va_degree: Voltage angle in degrees
        name: Name of the external grid
    
    Returns:
        Dict with status and new external grid index
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        ext_grid_idx = pp.create_ext_grid(net, bus=bus, vm_pu=vm_pu,
                                          va_degree=va_degree, name=name)
        return {
            "status": "success",
            "message": f"External grid added at bus {bus}",
            "ext_grid_index": int(ext_grid_idx),
            "total_ext_grids": len(net.ext_grid)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_contingency_analysis(contingency_type: str = "line",
                             element_indices: Optional[List[int]] = None) -> Dict[str, Any]:
    """Run N-1 contingency analysis on the current network.
    
    Args:
        contingency_type: Type of contingency ('line', 'trafo', or 'gen')
        element_indices: List of element indices to analyze (None for all)
    
    Returns:
        Dict containing contingency analysis results
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        net = _get_network()
        
        # Determine indices to analyze
        if element_indices is None:
            if contingency_type == "line":
                indices = list(net.line.index)
            elif contingency_type == "trafo":
                indices = list(net.trafo.index)
            elif contingency_type == "gen":
                indices = list(net.gen.index)
            else:
                return {"status": "error", "message": f"Unknown contingency type: {contingency_type}"}
        else:
            indices = element_indices
        
        results = []
        base_case_converged = False
        base_losses = 0.0
        
        # Run base case first
        try:
            pp.runpp(net)
            base_case_converged = net.converged
            base_losses = float(net.res_line["pl_mw"].sum())
        except:
            base_case_converged = False
        
        # Store original state
        orig_net = copy.deepcopy(net)
        
        # Run contingency for each element
        for idx in indices:
            contingency_net = copy.deepcopy(orig_net)
            
            try:
                contingency_net[contingency_type].at[idx, 'in_service'] = False
                pp.runpp(contingency_net)
                
                # Check for violations
                voltage_violations = contingency_net.res_bus[
                    (contingency_net.res_bus.vm_pu < 0.95) | 
                    (contingency_net.res_bus.vm_pu > 1.05)
                ].index.tolist()
                
                loading_violations = contingency_net.res_line[
                    contingency_net.res_line.loading_percent > 100
                ].index.tolist()
                
                results.append({
                    "contingency": f"{contingency_type}_{idx}",
                    "converged": contingency_net.converged,
                    "voltage_violations": voltage_violations,
                    "loading_violations": loading_violations,
                    "max_loading_percent": float(contingency_net.res_line["loading_percent"].max()),
                    "min_voltage_pu": float(contingency_net.res_bus["vm_pu"].min()),
                    "max_voltage_pu": float(contingency_net.res_bus["vm_pu"].max())
                })
            except Exception as e:
                results.append({
                    "contingency": f"{contingency_type}_{idx}",
                    "converged": False,
                    "error": str(e)
                })
        
        # Restore original network
        pp.runpp(orig_net)
        
        return {
            "status": "success",
            "message": f"Contingency analysis completed for {len(indices)} {contingency_type}(s)",
            "base_case_converged": base_case_converged,
            "base_case_losses_mw": base_losses,
            "contingency_results": results
        }
        
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Contingency analysis failed: {str(e)}"}


def get_available_std_types() -> Dict[str, Any]:
    """Get available standard types for lines and transformers.
    
    Returns:
        Dict with available standard types
    """
    if not PANDAPOWER_AVAILABLE:
        return {"status": "error", "message": "pandapower is not installed"}
    
    try:
        empty_net = pp.create_empty_network()
        line_types = list(pp.available_std_types(empty_net, "line").index)[:20]
        trafo_types = list(pp.available_std_types(empty_net, "trafo").index)[:20]
        
        return {
            "status": "success",
            "line_std_types_sample": line_types,
            "trafo_std_types_sample": trafo_types,
            "note": "Showing first 20 of each type. Many more available."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Export all public functions
__all__ = [
    'PANDAPOWER_AVAILABLE',
    'create_empty_network',
    'create_test_network',
    'load_network',
    'run_power_flow',
    'run_dc_power_flow',
    'get_network_info',
    'add_bus',
    'add_line',
    'add_load',
    'add_generator',
    'add_ext_grid',
    'run_contingency_analysis',
    'get_available_std_types',
]
