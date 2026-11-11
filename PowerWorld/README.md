# PowerWorld MCP Server

MCP server for PowerWorld Simulator via Easy SimAuto (ESA), enabling power flow analysis, contingency evaluation, and system studies.

## Requirements

- Python 3.11 or higher
- [Easy SimAuto (ESA)](https://github.com/mzy2240/ESA)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python powerworld_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "powerworld": {
      "command": "python",
      "args": ["PowerWorld/powerworld_mcp.py"]
    }
  }
}
```

## Available Tools

- **open_case(case_path: str)**: Open a PowerWorld case file and return basic case information.
- **run_powerflow(solution_method: str = 'RECTNEWT')**: Run power flow analysis with specified solution method and return results including overflows and voltage violations.
- **analyze_contingencies(option: str = "N-1", validate: bool = False)**: Perform N-1 or N-2 contingency analysis and return violation results.
- **get_power_flow_results(object_type: str, additional_fields: Optional[List[str]] = None)**: Get power flow results for specified object type (bus, gen, load, shunt, branch) with optional additional fields.
- **get_key_field_list(object_type: str)**: Get the list of key fields for a given object type.
- **change_parameters_multiple_element(object_type: str, param_list: List[str], value_list: List[List[Any]])**: Change parameters for multiple elements of the same type.
- **change_and_confirm_params(object_type: str, command_df: Dict[str, List[Any]])**: Change parameters and verify the changes were applied correctly.
- **get_ybus(full: bool = False)**: Get the bus admittance matrix (Ybus) of the system in full or sparse format.
- **to_graph(node: str = 'bus', geographic: bool = False, directed: bool = False)**: Convert the power system to a NetworkX graph representation.
- **get_jacobian(full: bool = False)**: Get the power flow Jacobian matrix in full or sparse format.
- **get_lodf_matrix(precision: int = 3, ignore_open_branch: bool = True, method: str = 'DC')**: Get the Line Outage Distribution Factors (LODF) matrix.
- **determine_shortest_path(start: str, end: str, branch_distance_measure: str = "X", branch_filter: str = "ALL")**: Find the shortest path between two buses.
- **run_robustness_analysis()**: Perform robustness analysis on the power system.
- **get_ptdf_matrix_fast()**: Get the Power Transfer Distribution Factors (PTDF) matrix using fast calculation method.

## Prompt Example

Could you perform an N-1 contingency analysis using PowerWorld on the case file "yourpath\PowerMCP\PowerWorld\IEEE 39 bus.pwb"? Based on the results, please provide suggestions for enhancing the system's security.

## Resources

- [Easy SimAuto (ESA) Documentation](https://github.com/mzy2240/ESA)
- [PowerWorld Simulator](https://www.powerworld.com/)
