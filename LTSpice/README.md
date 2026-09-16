# LTSpice MCP Server

MCP server for LTSpice electronic circuit simulation, enabling automated netlist generation, headless simulation, and result plotting.

## Requirements

- Python 3.10 or higher
- [PyLTSpice](https://github.com/nunobrum/LTSpice)
- LTSpice installed on your system (or via Wine on macOS/Linux)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Setup

Before running, you must configure the path to your LTspice executable in `ltspice_mcp.py`:
```python
# Default for Windows:
LTSPICE_EXECUTABLE_PATH = r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe"
```

## Usage

Run the MCP server:
```bash
python ltspice_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "ltspice": {
      "command": "python",
      "args": ["LTSpice/ltspice_mcp.py"]
    }
  }
}
```

## Available Tools

- **create_simulation_session(netlist_text: str)**: Create a new session with a timestamped directory and netlist file.
- **run_simulation(netlist_path: str, session_dir: str)**: Run LTSpice simulation in batch mode.
- **list_available_traces(raw_file_path: str)**: List available signals (traces) from a simulation's raw output.
- **plot_specific_traces(raw_file_path: str, session_dir: str, trace_names: list[str])**: Plot specified voltage and current traces using matplotlib.
- **read_simulation_log(log_file_path: str)**: Read simulation log files for debugging.
- **create_rc_transient_netlist(...)**: Helper to create a standard RC circuit netlist.
- **view_netlist_in_ltspice(netlist_path: str)**: Open netlist in LTSpice GUI.

## Tool results

Every tool returns the shape the whole distribution uses:

```json
{"status": "success", "...": "the keys that tool documents"}
{"status": "error", "message": "what went wrong"}
```

spicelib and matplotlib are imported by the two tools that need them, not at
startup, so the server runs and lists its tools with either one absent.
`list_available_traces` and `plot_specific_traces` then report which package to
install. The other tools need neither.

## Prompt Example

Could you create a simple RC circuit netlist with a 1k resistor and 1uF capacitor, run a transient simulation for 5ms, and plot the output voltage?

## Resources

- [PyLTSpice Documentation](https://pyltspice.readthedocs.io/)
- [LTSpice Simulator](https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html)
