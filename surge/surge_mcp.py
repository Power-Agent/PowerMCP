from typing import Dict, List, Optional, Tuple, Any, Union
import surge
from mcp.server.fastmcp import FastMCP
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server with logging
logger.info("Initializing Surge Analysis Server")
mcp = FastMCP("Surge Analysis Server")

# Global variable to store the current network
_current_net = None

def _get_network():
    """Get the current surge network instance.
    
    Returns:
        The current network or raises error if none loaded
    """
    global _current_net
    
    if _current_net is None:
        raise RuntimeError("No surge network is currently loaded. Please load a network first.")
    return _current_net


@mcp.tool()
def load_network(file_path: str) -> Dict[str, Any]:
    """Load a surge network from a file.
    
    Args:
        file_path: Path to the network file (e.g., .surge.json.zst)
        
    Returns:
        Dict containing status and simple message
    """
    logger.info(f"Loading network from file: {file_path}")
    global _current_net
    try:
        _current_net = surge.load(file_path)
            
        return {
            "status": "success",
            "message": f"Network loaded successfully from {file_path}"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"File not found: {file_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load network: {str(e)}"
        }

@mcp.tool()
def run_power_flow(algorithm: str = 'ac') -> Dict[str, Any]:
    """Run power flow analysis on the current network.
    
    Args:
        algorithm: Power flow algorithm ('ac' for AC, 'dc' for DC)
        
    Returns:
        Dict containing power flow results
    """
    logger.info(f"Running power flow analysis (algorithm: {algorithm})")
    try:
        net = _get_network()
        
        if algorithm.lower() == 'ac':
            # Run AC power flow
            sol = surge.solve_ac_pf(net)
            
            results = {
                "converged": getattr(sol, "converged", None),
                "iterations": getattr(sol, "iterations", None),
                "max_mismatch": getattr(sol, "max_mismatch", None)
            }
            message = "AC power flow completed"
            
        elif algorithm.lower() == 'dc':
            # Run DC power flow
            sol = surge.solve_dc_pf(net)
            
            results = {
                "converged": getattr(sol, "converged", True),
                "solve_time_secs": getattr(sol, "solve_time_secs", None)
            }
            message = "DC power flow completed"
        else:
            raise ValueError("Unsupported algorithm. Use 'ac' or 'dc'.")
            
        return {
            "status": "success",
            "message": message,
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
def run_contingency_analysis(contingency_type: str = "N-1") -> Dict[str, Any]:
    """Run contingency analysis on the current network.
    
    Args:
        contingency_type: Type of contingency analysis ("N-1")
        
    Returns:
        Dict containing contingency analysis results
    """
    logger.info(f"Running {contingency_type} contingency analysis")
    try:
        net = _get_network()
        
        if contingency_type.upper() == "N-1":
            sol = surge.analyze_n1_branch(net)
            
            results = {
                "n_with_violations": getattr(sol, "n_with_violations", None),
            }
            
            return {
                "status": "success",
                "message": "N-1 branch contingency analysis completed",
                "results": results
            }
        else:
            return {
                "status": "error",
                "message": f"Unsupported contingency type: {contingency_type}. Use 'N-1'."
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
    """Get general information about the current network.
    
    Returns:
        Dict containing status and available information
    """
    logger.info("Retrieving network information")
    try:
        net = _get_network()
        
        # We may not know the exact schema of the network but try some common properties
        # In a real scenario we'd query fields of 'net' object
        info = {}
        for prop in ["buses", "lines", "generators", "loads"]:
            if hasattr(net, prop):
                val = getattr(net, prop)
                if hasattr(val, "__len__"):
                    info[prop] = len(val)
                else:
                    info[prop] = "Present but uncountable via len()"
                    
        if not info:
             info["note"] = "Network object loaded but simple len() properties could not be auto-discovered."
        
        return {
            "status": "success",
            "message": "Network information retrieved",
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

if __name__ == "__main__":
    mcp.run(transport="stdio")
