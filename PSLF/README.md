# PSLF MCP Server

MCP server for PSLF (GE Positive Sequence Load Flow), enabling case management, power flow, and contingency analysis.

## Requirements

- Python 3.11 or higher
- PSLF with PSLF_PYTHON API
- [pandas](https://pandas.pydata.org/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python pslf_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "pslf": {
      "command": "python",
      "args": ["PSLF/pslf_mcp.py"]
    }
  }
}
```

## Available Tools

- **open_case(case: str)**: Open a PSLF case file (.sav).
- **save_case()**: Save the current case to temp.sav.
- **solve_case()**: Solve power flow using PSLF.
- **get_power_flow_results()**: Get power flow results for buses, branches, generators, loads.
- **analyze_contingencies()**: Run contingency analysis and return violation results.

## Resources

- [PSLF Documentation](https://www.gevernova.com/energy/energy-software/positive-sequence-load-flow-pslf)
