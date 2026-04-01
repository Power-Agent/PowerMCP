# Surge MCP Server

MCP server for surge power system analysis workspace, enabling network loading, power flow, and contingency analysis.

## Requirements

- Python 3.10 or higher
- [surge-py](https://pypi.org/project/surge-py/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python surge_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "surge": {
      "command": "python",
      "args": ["surge/surge_mcp.py"]
    }
  }
}
```

## Available Tools

- **load_network(file_path: str)**: Load a network from a file (`.surge.json.zst`).
- **run_power_flow(algorithm: str)**: Run power flow analysis (`ac` or `dc`).
- **run_contingency_analysis(contingency_type: str)**: Run pre-defined contingency analyses (e.g. `N-1`).
- **get_network_info()**: Run a basic inspection on the loaded network object.

## Prompt Example

Could you perform an AC power flow using Surge on the case file `yourpath\surge\surge\test_case.surge.json.zst`? Based on the results, is it converged?

## Resources

- [Surge GitHub Repository](https://github.com/amptimal/surge)
