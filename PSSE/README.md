# PSSE MCP Server

MCP server for PSS/E (Siemens PTI) power system analysis. Supports PSSE 35+ with Python 3.

## Requirements

- Python 3.10 or higher
- PSSE 35+ installed with Python API (PSSPY)
- [mcp](https://pypi.org/project/mcp/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python psse_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "psse": {
      "command": "python",
      "args": ["PSSE/psse_mcp.py"]
    }
  }
}
```

## Available Tools

- **open_case(case: str)**: Open a PSSE case file.
- **solve_case()**: Solve power flow using PSSE Newton-Raphson method.
- **run_psspy_command(function_name, arguments)**: Execute an allowed psspy API command by name using the JSON reference spec. Commands that load or execute external code are excluded.
- **lookup_psspy_command(function_name)**: Look up the API reference for a psspy function without executing it.
- **search_psspy_commands(query, category)**: Search the psspy API index for functions matching a query.
- **list_dynamic_output_channels(outfile, outvrsn)**: List the channels recorded in a dynamic simulation output file (`.out`/`.outx`).
- **read_dynamic_output(outfile, channels, outvrsn, max_points, max_cells)**: Read selected time series (all channels when omitted). Responses default to a 10,000-point cap and a 100,000-cell budget; the effective point cap is the lower of these limits. Sampling is deterministic and endpoint-preserving. When downsampled, full-resolution per-channel extrema are also returned.

## Prompt Example

- use psse run power flow of "yourpath\PowerMCP\PSSE\savnw.sav"

## Resources

- [PSS/E Documentation](https://www.siemens-energy.com/)
