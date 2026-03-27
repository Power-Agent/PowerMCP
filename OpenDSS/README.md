# OpenDSS MCP Server

MCP server for OpenDSS distribution studies using `py_dss_toolkit` and `py_dss_interface`, enabling the following capabilities: compile model, get model data, perform snapshot power flow, and get results.

## Requirements

- Python 3.10 or higher
- Install from the **PowerMCP** repository root so the editable path resolves:

```bash
pip install -r OpenDSS/requirements.txt
```

## Usage

Run the MCP server:

```bash
python opendss_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "opendss": {
      "command": "python",
      "args": ["OpenDSS/opendss_mcp.py"]
    }
  }
}
```

## Available Tools

Responses are JSON with `success` and either `payload` (tabular data) or `error`.


| Tool | Purpose |
|------|---------|
| **compile_opendss_file** | `ClearAll` + `Compile`; `payload` includes `circuit_readiness` and `circuit_loaded: true` |
| **clear_all_opendss_memory** | `ClearAll`; resets `circuit_loaded` and `solution_available` |
| **get_model_summary_records** | `model._summary_model_records` |
| **get_buses_records** | `model._buses_records` |
| **get_lines_records** | `model._lines_records` (`payload` null if no lines) |
| **add_line_in_vsource** | `model.add_line_in_vsource` — feeder-head line; optional meter/monitors; clears `solution_available` (re-solve after) |
| **solve_opendss_snapshot** | Requires compiled circuit; sets `solution_available: true`; `payload` includes solve status fields |
| **get_results_summary_records** | `results._summary_records` (after solve) |
| **get_voltage_mag_ln_nodes_records** | `results._voltage_mag_ln_nodes_records` |
| **get_powers_p_records** | `results._powers_p_records` |

## Example

What are the voltages at all buses in the IEEE 13-bus feeder?
The DSS file is located at <path_to_your_dss_file>

## Resources

- [OpenDSS](https://opendss.epri.com/IntroductiontoOpenDSS.html)
- [py-dss-interface](https://github.com/PauloRadatz/py_dss_interface)
- [py-dss-toolkit](https://github.com/PauloRadatz/py_dss_toolkit)
