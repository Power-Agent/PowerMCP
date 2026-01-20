from typing import Dict, List, Optional, Tuple, Any, Union
import pandapower as pp
from mcp.server.fastmcp import FastMCP
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import PowerError, power_mcp_tool

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


@power_mcp_tool(mcp)
def create_empty_network() -> Dict[str, Any]:
    """Create an empty pandapower network.
    
    Returns:
        Dict containing status and network information
    """
    logger.info("Creating an empty pandapower network")
    global _current_net
    try:
        _current_net = pp.create_empty_network()
        raise Exception("test")
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
        return PowerError(
            status="error",
            message=f"Failed to create empty network: {str(e)}"
        )

@power_mcp_tool(mcp)
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
        return PowerError(
            status="error",
            message=f"File not found: {file_path}"
        )
    except ValueError as ve:
        return PowerError(
            status="error",
            message=str(ve)
        )
    except Exception as e:
        return PowerError(
            status="error",
            message=f"Failed to load network: {str(e)}"
        )

@power_mcp_tool(mcp)
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
        return PowerError(
            status="error",
            message=str(re)
        )
    except Exception as e:
        return PowerError(
            status="error",
            message=f"Power flow calculation failed: {str(e)}"
        )

@power_mcp_tool(mcp)
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
        return PowerError(
            status="error",
            message=str(re)
        )
    except Exception as e:
        return PowerError(
            status="error",
            message=f"Contingency analysis failed: {str(e)}"
        )

@power_mcp_tool(mcp)
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
        return PowerError(
            status="error",
            message=str(re)
        )
    except Exception as e:
        return PowerError(
            status="error",
            message=f"Failed to get network information: {str(e)}"
        )

if __name__ == "__main__":
    mcp.run(transport="stdio") 