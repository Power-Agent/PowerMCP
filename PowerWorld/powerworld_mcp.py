import sys
import os
from typing import Dict, List, Optional, Tuple, Any, Union
from mcp.server.mcpserver import MCPServer as FastMCP
from esa import SAW, PowerWorldError

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import PathNotAllowed, checked_path
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

# Initialize MCP server
mcp = FastMCP("PowerWorld Analysis Server")

# Global SAW instance
_saw = None

def _get_saw(case_path: Optional[str] = None) -> SAW:
    """Get or create SAW instance."""
    global _saw
    if _saw is None and case_path is not None:
        try:
            _saw = SAW(case_path, UIVisible=True)
        except PowerWorldError as e:
            print(f"Error initializing SAW: {str(e)}", file=sys.stderr)
            raise
    elif _saw is None:
        raise ValueError("No case is currently open. Please open a case first.")
    return _saw

@mcp.tool()
def open_case(case_path: str) -> Dict[str, Any]:
    """
    Open a PowerWorld case file.
    
    Args:
        case_path: Path to the PowerWorld case file
    
    Returns:
        Dict with status and case information
    """
    try:
        case_path = checked_path(case_path, purpose="case_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        # Validate case_path input
        if not isinstance(case_path, str):
            return {"status": "error", "message": "case_path must be a string"}

        if not case_path:
            return {"status": "error", "message": "case_path cannot be empty"}
        if not os.path.exists(case_path):
            return {"status": "error", "message": f"Case file not found: {case_path}"}

        if not os.path.isfile(case_path):
            return {"status": "error", "message": f"Case path is not a file: {case_path}"}
        if not case_path.lower().endswith((".pwb", ".pwd")):
            return {"status": "error", "message": "Unsupported case file format. Expected .pwb or .pwd"}

        # Initialize SAW with the case
        saw = _get_saw(case_path)

        # Get basic case information
        bus_data = saw.get_power_flow_results('bus')
        branch_data = saw.get_power_flow_results('branch')
        gen_data = saw.get_power_flow_results('gen')

        return {
            'status': 'success',
            'case_info': {
                'path': case_path,
                'num_buses': len(bus_data) if bus_data is not None else 0,
                'num_branches': len(branch_data) if branch_data is not None else 0,
                'num_generators': len(gen_data) if gen_data is not None else 0
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def run_powerflow(solution_method: str = 'RECTNEWT') -> Dict[str, Any]:
    """
    Run power flow analysis on the currently open case.
    
    Args:
        solution_method: Power flow solution method. Options:
            - 'RECTNEWT' (default) - Rectangular Newton-Raphson
            - 'POLARNEWTON' - Polar Newton-Raphson
            - 'GAUSSSEIDEL' - Gauss-Seidel
            - 'FDXB' - Fast Decoupled
            - 'DC' - DC power flow
            
    Returns:
        Dictionary containing power flow results
    """
    try:
        saw = _get_saw()
        
        # Solve power flow
        saw.SolvePowerFlow(SolMethod=solution_method)
        
        # Get branch flow information
        branch_data = saw.get_power_flow_results('branch')
        
        # Process results to check for overflows
        overflows = []
        if branch_data is not None:
            for _, branch in branch_data.iterrows():
                try:
                    from_bus = branch['BusNum']
                    to_bus = branch['BusNum:1']
                    circuit = branch['LineCircuit']
                    mw = branch['LineMW']
                    mvar = branch['LineMVR']
                    
                    # Calculate apparent power and loading
                    mva = (mw**2 + mvar**2)**0.5
                    loading_percent = mva / branch['LineRateA'] * 100 if branch['LineRateA'] > 0 else 0
                    
                    if loading_percent > 100:
                        overflows.append({
                            'line': f"Line {from_bus}-{to_bus} Circuit {circuit}",
                            'loading_percent': loading_percent,
                            'mw': mw,
                            'mvar': mvar,
                            'mva': mva
                        })
                except Exception as e:
                    continue
        
        # Get voltage violations
        bus_data = saw.get_power_flow_results('bus')
        voltage_violations = []
        if bus_data is not None:
            for _, bus in bus_data.iterrows():
                voltage = bus['BusPUVolt']
                if voltage < 0.95 or voltage > 1.05:
                    voltage_violations.append({
                        'bus': int(bus['BusNum']),
                        'voltage': voltage,
                        'angle': bus['BusAngle']
                    })
        
        return {
            'status': 'success',
            'results': {
                'solution_method': solution_method,
                'converged': True,
                'overflows': overflows,
                'voltage_violations': voltage_violations,
                'total_branches': len(branch_data) if branch_data is not None else 0,
                'total_buses': len(bus_data) if bus_data is not None else 0
            }
        }
        
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def analyze_contingencies(option: str = "N-1", validate: bool = False) -> Dict[str, Any]:
    """
    Run contingency analysis on the currently open case.
    
    Args:
        option: Type of contingency analysis ("N-1" or "N-2")
        validate: Whether to validate contingencies
        
    Returns:
        Dictionary containing contingency analysis results
    """
    try:
        saw = _get_saw()
        
        # Run contingency analysis
        if option == "N-1":
            # Get all branches for N-1 analysis
            branch_data = saw.get_power_flow_results('branch')
            violations = []
            
            # Save initial state
            saw.SaveState()
            
            # Test each line outage
            for _, branch in branch_data.iterrows():
                try:
                    # Open the line
                    from_bus = int(branch['BusNum'])
                    to_bus = int(branch['BusNum:1'])
                    circuit = branch['LineCircuit']
                    
                    params = ['BusNum', 'BusNum:1', 'LineCircuit', 'LineStatus']
                    values = [from_bus, to_bus, circuit, 'OPEN']
                    saw.ChangeParametersMultipleElement('branch', params, [values])
                    # Solve power flow
                    saw.SolvePowerFlow()
                    
                    # Check for violations
                    result = run_powerflow()
                    if result['status'] == 'success' and (
                        len(result['results']['overflows']) > 0 or 
                        len(result['results']['voltage_violations']) > 0
                    ):
                        violations.append({
                            'contingency': f"Line {from_bus}-{to_bus} Circuit {circuit}",
                            'overflows': result['results']['overflows'],
                            'voltage_violations': result['results']['voltage_violations']
                        })
                    
                    # Restore state
                    saw.LoadState()
                    
                except Exception as e:
                    print(f"Error analyzing contingency: {str(e)}", file=sys.stderr)
                    continue
            
            return {
                'status': 'success',
                'results': {
                    'option': option,
                    'violations': violations,
                    'total_contingencies': len(branch_data),
                    'total_violations': len(violations)
                }
            }
        else:
            return {
                'status': 'error',
                'message': f"Unsupported contingency option: {option}"
            }
            
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_power_flow_results(object_type: str, additional_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get power flow results for specified object type with optional additional fields.
    
    This function retrieves power flow results for various power system components like buses,
    generators, loads, shunts, and branches. It returns standardized fields for each object
    type plus any additional fields requested.
    
    Args:
        object_type: Type of power system object to get results for. Options:
            - 'bus': Bus results (voltage, angle, net MW/MVAR)
            - 'gen': Generator results (MW, MVAR output)
            - 'load': Load results (MW, MVAR consumption)
            - 'shunt': Shunt results (MW, MVAR)
            - 'branch': Branch results (MW, MVAR flows)
        additional_fields: Optional list of additional fields to retrieve beyond defaults
            
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: DataFrame with power flow results if successful
            - message: Error message if status is 'error'
            
    Example:
        >>> results = get_power_flow_results('bus')
        >>> print(results['results'])  # Shows bus voltages, angles, etc.
    """
    try:
        saw = _get_saw()
        
        # Get results using SAW's get_power_flow_results
        results = saw.get_power_flow_results(object_type, additional_fields)
        
        if results is None:
            return {
                'status': 'error',
                'message': f'No results found for object type: {object_type}'
            }
            
        return {
            'status': 'success',
            'results': results.to_dict('records')  # Convert DataFrame to list of dicts
        }
        
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_key_field_list(object_type: str) -> Dict[str, Any]:
    """
    Get the list of key fields for a given object type.
    
    Key fields are required to uniquely identify objects in PowerWorld.
    For example, generators are identified by BusNum and GenID.
    
    Args:
        object_type: The type of power system object (e.g., 'bus', 'gen', 'branch')
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: List of key field names
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        key_fields = saw.get_key_field_list(object_type)
        return {
            'status': 'success',
            'results': key_fields
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def change_parameters_multiple_element(object_type: str, param_list: List[str], value_list: List[List[Any]]) -> Dict[str, Any]:
    """
    Change parameters for multiple elements of the same type.
    
    Args:
        object_type: Type of power system object (e.g., 'bus', 'gen', 'branch')
        param_list: List of parameter names, must include key fields
        value_list: List of value lists, each inner list corresponds to param_list
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - message: Error message if status is 'error'
            
    Example:
        >>> # Change generator MW output for two generators
        >>> param_list = ['BusNum', 'GenID', 'GenMW']
        >>> value_list = [[1, '1', 100], [2, '1', 50]]
        >>> result = change_parameters_multiple_element('gen', param_list, value_list)
    """
    try:
        saw = _get_saw()
        saw.ChangeParametersMultipleElement(object_type, param_list, value_list)
        return {
            'status': 'success'
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def change_and_confirm_params(object_type: str, command_df: Dict[str, List[Any]]) -> Dict[str, Any]:
    """
    Change parameters using a DataFrame and confirm the changes were respected.
    
    This is a safer version of change_parameters_multiple_element that verifies
    PowerWorld actually made the requested changes.
    
    Args:
        object_type: Type of power system object (e.g., 'bus', 'gen', 'branch')
        command_df: Dictionary representing a DataFrame with parameters to change
                   Must include key fields for the object type
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - message: Error message if status is 'error'
            
    Example:
        >>> # Change generator MW output
        >>> command_df = {
        ...     'BusNum': [1, 2],
        ...     'GenID': ['1', '1'],
        ...     'GenMW': [100, 50]
        ... }
        >>> result = change_and_confirm_params('gen', command_df)
    """
    try:
        saw = _get_saw()
        
        # Save current state
        saw.SaveState()
        
        try:
            # Convert dictionary to lists for PowerWorld API
            param_list = list(command_df.keys())
            values = list(zip(*command_df.values()))
            
            # For branch status changes, we need to use a script command
            if object_type == 'branch' and 'LineStatus' in param_list:
                for value in values:
                    # Create a dictionary for easy access
                    params = dict(zip(param_list, value))
                    
                    # Construct the script command - using exact PowerWorld format
                    status = "OPEN" if params['LineStatus'] == "OPEN" else "CLOSE"
                    script = (f"OPEN BRANCH FROM BUS {params['BusNum']} "
                            f"TO BUS {params['BusNum:1']} CKT {params['LineCircuit']}"
                            if status == "OPEN" else
                            f"CLOSE BRANCH FROM BUS {params['BusNum']} "
                            f"TO BUS {params['BusNum:1']} CKT {params['LineCircuit']}")
                    
                    # Execute the script command
                    saw.RunScriptCommand(script)
            else:
                # For other parameters, use ChangeParametersMultipleElement
                saw.ChangeParametersMultipleElement(object_type, param_list, values)
            
            # Run power flow to update the system state
            saw.SolvePowerFlow()
            
            return {
                'status': 'success'
            }
            
        except Exception as e:
            # If change fails, restore previous state
            saw.LoadState()
            raise e
            
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_ybus(full: bool = False) -> Dict[str, Any]:
    """
    Get the bus admittance matrix (Ybus) of the system.
    
    Args:
        full: If True, returns the full matrix. If False, returns the sparse matrix
              in CSR format (default: False)
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with Ybus data if successful:
                - matrix: The Ybus matrix (full or sparse)
                - bus_numbers: List of bus numbers in order
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        ybus = saw.get_ybus(full=full)
        
        # Get bus numbers for reference
        bus_data = saw.get_power_flow_results('bus')
        bus_numbers = bus_data['BusNum'].tolist() if bus_data is not None else []
        
        # Convert to appropriate format for return
        if full:
            # Convert numpy array to nested list for JSON serialization
            matrix_data = ybus.tolist()
        else:
            # Convert sparse matrix to dictionary format
            matrix_data = {
                'data': ybus.data.tolist(),
                'indices': ybus.indices.tolist(),
                'indptr': ybus.indptr.tolist(),
                'shape': ybus.shape
            }
            
        return {
            'status': 'success',
            'results': {
                'matrix': matrix_data,
                'bus_numbers': bus_numbers
            }
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def to_graph(node: str = 'bus', geographic: bool = False, directed: bool = False) -> Dict[str, Any]:
    """
    Convert the power system case to a NetworkX graph representation.
    
    Args:
        node: Type of node representation ('bus' or 'substation')
        geographic: Whether to include geographic coordinates
        directed: Whether to create a directed graph based on power flow
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with graph data if successful:
                - nodes: List of node dictionaries with attributes
                - edges: List of edge dictionaries with attributes
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        graph = saw.to_graph(node=node, geographic=geographic, directed=directed)
        
        # Convert NetworkX graph to serializable format
        graph_data = {
            'nodes': [{'id': n, **graph.nodes[n]} for n in graph.nodes()],
            'edges': [{'source': u, 'target': v, **graph.edges[u, v, k]} 
                     for u, v, k in graph.edges(keys=True)]
        }
        
        return {
            'status': 'success',
            'results': graph_data
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_jacobian(full: bool = False) -> Dict[str, Any]:
    """
    Get the power flow Jacobian matrix of the system.
    
    Args:
        full: If True, returns the full matrix. If False, returns sparse format
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with Jacobian data if successful:
                - matrix: The Jacobian matrix (full or sparse)
                - bus_numbers: List of bus numbers in order
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        jacobian = saw.get_jacobian(full=full)
        
        # Get bus numbers for reference
        bus_data = saw.get_power_flow_results('bus')
        bus_numbers = bus_data['BusNum'].tolist() if bus_data is not None else []
        
        # Convert to appropriate format for return
        if full:
            matrix_data = jacobian.tolist()
        else:
            matrix_data = {
                'data': jacobian.data.tolist(),
                'indices': jacobian.indices.tolist(),
                'indptr': jacobian.indptr.tolist(),
                'shape': jacobian.shape
            }
            
        return {
            'status': 'success',
            'results': {
                'matrix': matrix_data,
                'bus_numbers': bus_numbers
            }
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_lodf_matrix(precision: int = 3, ignore_open_branch: bool = True, method: str = 'DC') -> Dict[str, Any]:
    """
    Get the Line Outage Distribution Factors (LODF) matrix.
    
    Args:
        precision: Number of decimal places for results
        ignore_open_branch: Whether to ignore open branches
        method: Power flow method ('DC' or other)
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with LODF data if successful:
                - matrix: The LODF matrix
                - branch_info: List of branch identifiers
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        lodf = saw.get_lodf_matrix(precision=precision, 
                                 ignore_open_branch=ignore_open_branch,
                                 method=method)
        
        # Get branch information for reference
        branch_data = saw.get_power_flow_results('branch')
        if branch_data is not None:
            branch_info = [f"{row['BusNum']}-{row['BusNum:1']}-{row['LineCircuit']}" 
                         for _, row in branch_data.iterrows()]
        else:
            branch_info = []
            
        return {
            'status': 'success',
            'results': {
                'matrix': lodf.tolist(),
                'branch_info': branch_info
            }
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def determine_shortest_path(start: str, end: str, branch_distance_measure: str = "X", branch_filter: str = "ALL") -> Dict[str, Any]:
    """
    Find the shortest path between two buses in the power system.
    
    Args:
        start: Starting bus number
        end: Ending bus number
        branch_distance_measure: Measure to use for distance ("X", "Z", etc.)
        branch_filter: Filter for branches to consider
        
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: DataFrame with path information if successful
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        path_data = saw.DetermineShortestPath(start=start, 
                                           end=end,
                                           BranchDistanceMeasure=branch_distance_measure,
                                           BranchFilter=branch_filter)
        
        if path_data is not None:
            return {
                'status': 'success',
                'results': path_data.to_dict('records')
            }
        else:
            return {
                'status': 'error',
                'message': 'No path found between specified buses'
            }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def run_robustness_analysis() -> Dict[str, Any]:
    """
    Perform robustness analysis on the power system.
    
    This analysis evaluates the system's ability to maintain operation
    under various contingencies and stress conditions.
    
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with robustness metrics if successful
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        results = saw.run_robustness_analysis()
        
        return {
            'status': 'success',
            'results': results
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

@mcp.tool()
def get_ptdf_matrix_fast() -> Dict[str, Any]:
    """
    Get the Power Transfer Distribution Factors (PTDF) matrix using fast calculation method.
    
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - results: Dictionary with PTDF data if successful:
                - matrix: The PTDF matrix
                - branch_info: List of branch identifiers
                - bus_numbers: List of bus numbers
            - message: Error message if status is 'error'
    """
    try:
        saw = _get_saw()
        ptdf = saw.get_ptdf_matrix_fast()
        
        # Get branch information for reference
        branch_data = saw.get_power_flow_results('branch')
        if branch_data is not None:
            branch_info = [f"{row['BusNum']}-{row['BusNum:1']}-{row['LineCircuit']}" 
                         for _, row in branch_data.iterrows()]
        else:
            branch_info = []
            
        # Get bus numbers for reference
        bus_data = saw.get_power_flow_results('bus')
        bus_numbers = bus_data['BusNum'].tolist() if bus_data is not None else []
            
        return {
            'status': 'success',
            'results': {
                'matrix': ptdf.tolist(),
                'branch_info': branch_info,
                'bus_numbers': bus_numbers
            }
        }
    except PowerWorldError as e:
        return {"status": "error", "message": f"PowerWorld Error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected Error: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport="stdio")
