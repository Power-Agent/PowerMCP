"""
PowerMCP PyPSA Module
Provides power system optimization tools using PyPSA.
"""

from typing import Dict, List, Optional, Any
import json

try:
    import pypsa
    PYPSA_AVAILABLE = True
except ImportError:
    PYPSA_AVAILABLE = False
    pypsa = None

# Global variable to store the current network
_current_net = None


def _get_network():
    """Get the current PyPSA network instance."""
    global _current_net
    if _current_net is None:
        raise RuntimeError("No PyPSA network is currently loaded. Please create or load a network first.")
    return _current_net


def _set_network(net):
    """Set the current PyPSA network instance."""
    global _current_net
    _current_net = net


def create_network(name: str = "PyPSA Network") -> Dict[str, Any]:
    """Create a new PyPSA network.
    
    Args:
        name: Name of the network
    
    Returns:
        Dict containing status and network information
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    global _current_net
    try:
        _current_net = pypsa.Network(name=name)
        return {
            "status": "success",
            "message": f"PyPSA network '{name}' created successfully",
            "network_name": name
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_network_info() -> Dict[str, Any]:
    """Get information about the current PyPSA network.
    
    Returns:
        Dict containing network statistics
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        return {
            "status": "success",
            "network_name": net.name,
            "component_counts": {
                "buses": len(net.buses),
                "generators": len(net.generators),
                "loads": len(net.loads),
                "lines": len(net.lines),
                "transformers": len(net.transformers),
                "storage_units": len(net.storage_units)
            }
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_bus(bus_id: str, v_nom: float = 380.0, x: Optional[float] = None,
            y: Optional[float] = None, carrier: str = "AC") -> Dict[str, Any]:
    """Add a bus to the current PyPSA network.
    
    Args:
        bus_id: Unique identifier for the bus
        v_nom: Nominal voltage in kV
        x: X coordinate (optional)
        y: Y coordinate (optional)
        carrier: Energy carrier (default: AC)
    
    Returns:
        Dict with status
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.add("Bus", bus_id, v_nom=v_nom, x=x, y=y, carrier=carrier)
        return {
            "status": "success",
            "message": f"Bus '{bus_id}' added to network",
            "total_buses": len(net.buses)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_generator(gen_id: str, bus: str, p_nom: float,
                  marginal_cost: float = 0.0, carrier: str = "generator",
                  p_min_pu: float = 0.0, p_max_pu: float = 1.0) -> Dict[str, Any]:
    """Add a generator to the current PyPSA network.
    
    Args:
        gen_id: Unique identifier for the generator
        bus: Bus to connect generator to
        p_nom: Nominal power in MW
        marginal_cost: Marginal cost
        carrier: Energy carrier
        p_min_pu: Minimum power output (per unit)
        p_max_pu: Maximum power output (per unit)
    
    Returns:
        Dict with status
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.add("Generator", gen_id, bus=bus, p_nom=p_nom,
                marginal_cost=marginal_cost, carrier=carrier,
                p_min_pu=p_min_pu, p_max_pu=p_max_pu)
        return {
            "status": "success",
            "message": f"Generator '{gen_id}' added to network",
            "total_generators": len(net.generators)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_load(load_id: str, bus: str, p_set: float) -> Dict[str, Any]:
    """Add a load to the current PyPSA network.
    
    Args:
        load_id: Unique identifier for the load
        bus: Bus to connect load to
        p_set: Active power consumption in MW
    
    Returns:
        Dict with status
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.add("Load", load_id, bus=bus, p_set=p_set)
        return {
            "status": "success",
            "message": f"Load '{load_id}' added to network",
            "total_loads": len(net.loads)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def add_line(line_id: str, bus0: str, bus1: str, x: float,
             r: float = 0.0, s_nom: float = 1000.0) -> Dict[str, Any]:
    """Add a line to the current PyPSA network.
    
    Args:
        line_id: Unique identifier for the line
        bus0: From bus
        bus1: To bus
        x: Reactance in Ohms
        r: Resistance in Ohms
        s_nom: Nominal power in MVA
    
    Returns:
        Dict with status
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.add("Line", line_id, bus0=bus0, bus1=bus1, x=x, r=r, s_nom=s_nom)
        return {
            "status": "success",
            "message": f"Line '{line_id}' added to network",
            "total_lines": len(net.lines)
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_power_flow() -> Dict[str, Any]:
    """Run power flow analysis on the current PyPSA network.
    
    Returns:
        Dict containing power flow results
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.pf()
        
        return {
            "status": "success",
            "message": "Power flow completed",
            "bus_results": {
                "v_mag_pu": net.buses_t.v_mag_pu.to_dict() if hasattr(net.buses_t, 'v_mag_pu') and len(net.buses_t.v_mag_pu) > 0 else {},
                "v_ang": net.buses_t.v_ang.to_dict() if hasattr(net.buses_t, 'v_ang') and len(net.buses_t.v_ang) > 0 else {}
            },
            "line_results": {
                "p0": net.lines_t.p0.to_dict() if hasattr(net.lines_t, 'p0') and len(net.lines_t.p0) > 0 else {},
                "p1": net.lines_t.p1.to_dict() if hasattr(net.lines_t, 'p1') and len(net.lines_t.p1) > 0 else {}
            }
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Power flow failed: {str(e)}"}


def run_optimal_power_flow() -> Dict[str, Any]:
    """Run optimal power flow on the current PyPSA network.
    
    Returns:
        Dict containing OPF results
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        status, termination_condition = net.optimize()
        
        return {
            "status": "success" if status == "ok" else "warning",
            "message": f"OPF completed with status: {status}",
            "termination_condition": str(termination_condition),
            "objective_value": float(net.objective) if hasattr(net, 'objective') else None,
            "generator_dispatch": net.generators_t.p.to_dict() if hasattr(net.generators_t, 'p') and len(net.generators_t.p) > 0 else {}
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"OPF failed: {str(e)}"}


def load_network(file_path: str) -> Dict[str, Any]:
    """Load a PyPSA network from a file.
    
    Args:
        file_path: Path to the network file (.nc or .h5)
    
    Returns:
        Dict containing status and network information
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    global _current_net
    try:
        _current_net = pypsa.Network(file_path)
        return {
            "status": "success",
            "message": f"Network loaded from {file_path}",
            "network_name": _current_net.name,
            "component_counts": {
                "buses": len(_current_net.buses),
                "generators": len(_current_net.generators),
                "loads": len(_current_net.loads),
                "lines": len(_current_net.lines)
            }
        }
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to load network: {str(e)}"}


def save_network(file_path: str) -> Dict[str, Any]:
    """Save the current PyPSA network to a file.
    
    Args:
        file_path: Path to save the network (.nc for NetCDF)
    
    Returns:
        Dict with status
    """
    if not PYPSA_AVAILABLE:
        return {"status": "error", "message": "pypsa is not installed"}
    
    try:
        net = _get_network()
        net.export_to_netcdf(file_path)
        return {
            "status": "success",
            "message": f"Network saved to {file_path}"
        }
    except RuntimeError as re:
        return {"status": "error", "message": str(re)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save network: {str(e)}"}


# Export all public functions
__all__ = [
    'PYPSA_AVAILABLE',
    'create_network',
    'get_network_info',
    'add_bus',
    'add_generator',
    'add_load',
    'add_line',
    'run_power_flow',
    'run_optimal_power_flow',
    'load_network',
    'save_network',
]
