# DIgSILENT PowerFactory MCP Agent

A Model Context Protocol (MCP) server that exposes DIgSILENT PowerFactory simulation capabilities to AI assistants such as Claude. The agent automates RMS transient stability simulations, load flow and short-circuit calculations, parameter modifications, and result exports — all through a clean, tool-callable interface.

---

## Architecture

```
Claude / AI assistant
        │  MCP protocol
        ▼
MCP_PowerFactory.py   ← MCP server (FastMCP)
        │  Python calls 
        ▼
Agent_DIgSILENT.py    ← Simulation engine
        │  
        ▼
DIgSILENT PowerFactory 
        │
        ▼
Output folder:  CSV results · PNG plots · optional .pfd export
```

---

## Features

- **Full simulation pipeline** — connect, activate study case, load flow, RMS transient simulation, CSV export, plot generation, optional PFD export in one call.
- **Custom fault scenarios** — define bus faults, line faults, and generator switching events at call time without editing config files.
- **Parameter modification** — update any PowerFactory attribute on any object via the MCP interface.
- **Load flow and short-circuit** — run Load flow and Short-Circuit calculation.
- **Automatic plot generation** — bus voltage magnitudes and generator speeds plotted from exported CSV results.
- **Study case management** — create, copy, and activate study cases with idempotency support (replay-safe via `request_id`).
- **Project import/export** — import `.pfd` files and export the active project back to `.pfd`.
- **CSV result reading** — auto-discovers the latest result file or reads a specified path.
- **JSON configuration** — all simulation parameters controlled through `simulation_config.json`.

---

## Implemented Functions

### MCP Tools (`MCP_PowerFactory.py`)

| Tool | Description |
|------|-------------|
| `ping` | Health check — returns `"pong"`. |
| `close_digsilent` | Closes the PowerFactory session. |
| `get_config` | Returns the active `simulation_config.json` as a JSON string. |
| `import_project` | Imports a `.pfd` project file and activates it. |
| `create_study_case` | Creates (or activates) a study case by name, copying from a base case when needed. Supports `request_id` for idempotency. |
| `modify_parameter` | Sets one attribute on all PowerFactory objects matching a query string. Auto-casts string values to the correct type. |
| `run_loadflow` | Runs a standalone load flow calculation (ComLdf). |
| `run_short_circuit` | Runs a standalone short-circuit calculation (ComShc). |
| `run_simulation` | Executes the full pipeline defined in `simulation_config.json`. |
| `run_custom_case` | Runs one fault simulation with parameters supplied at call time (no config file edit required). |
| `read_results_csv` | Reads an RMS result CSV; auto-discovers the latest file if no path is given. |

### Simulation Engine (`Agent_DIgSILENT.py`)

| Class / Method | Description |
|----------------|-------------|
| `SimulationConfig` | Dataclass holding all simulation parameters. `from_json()` loads from a JSON file. |
| `Logger` | Timestamped console logging with `info`, `ok`, `warn`, `error`, `section`. |
| `DIgSILENTAgent.__init__` | Initialises the agent from a `SimulationConfig`. |
| `DIgSILENTAgent.connect` | Connects to PowerFactory and activates the configured project. |
| `DIgSILENTAgent.activate_study_case` | Activates or creates the target study case. |
| `DIgSILENTAgent.run_loadflow` | Executes ComLdf. |
| `DIgSILENTAgent.run_rms_simulation` | Applies fault events, then runs ComInc + ComSim. |
| `DIgSILENTAgent._apply_fault_event` | Builds the event sequence for bus faults, line faults, or generator switches. |
| `DIgSILENTAgent.addSwitchEvent` | Creates a PowerFactory `EvtSwitch` event. |
| `DIgSILENTAgent.export_results_to_csv` | Exports the RMS result object to CSV via ComRes. |
| `DIgSILENTAgent.export_project_to_pfd` | Exports the active project to `.pfd` via ComPfdexport. |
| `DIgSILENTAgent.generate_standard_plots` | Reads the exported CSV and produces voltage and generator speed PNG plots. |
| `DIgSILENTAgent.import_project` | Imports a `.pfd` file into the running PowerFactory session. |
| `DIgSILENTAgent.create_study_case` | Creates or reuses a study case by exact name. |
| `DIgSILENTAgent.modify_parameter` | Sets an attribute on all objects returned by `GetCalcRelevantObjects`. |
| `DIgSILENTAgent.short_circuit` | Standalone ComShc execution. |
| `DIgSILENTAgent.run_pipeline` | Orchestrates the full workflow and returns a structured status report. |
| `DIgSILENTAgent.close` | Shuts down PowerFactory and clears shared handles. |

---

## Configuration

Copy `simulation_config.example.json` to `simulation_config.json` and fill in your paths and parameters:

```json
{
    "project_path":    "\\<username>\\<project_folder>\\<project_name>.IntPrj",
    "study_case":      "Case 1",
    "base_study_case": "0. Base",
    "output_dir":      "C:\\path\\to\\output",
    "run_label":       "Test_1",
    "result_name":     "All calculations.ElmRes",
    "cases": [
        {
            "case_name":     "Fault_1",
            "fault_type":    "bus",
            "fault_element": "Bus 25.ElmTerm",
            "t_start": 0.0, "t_fault": 1.0, "t_clear": 1.08, "t_end": 10.0, "dt_rms": 0.01
        }
    ]
}
```

Supported `fault_type` values: `"bus"`, `"line"`, `"gen_switch"`.


---

## Output Structure

Each simulation run creates a dedicated subfolder:

```
output_dir/
└── run_label/
    ├── run_label_RMS.csv
    ├── run_label_voltages.png
    ├── run_label_gen_speeds.png
    └── run_label.pfd          (optional)
```

---

## Requirements

See [requirements.txt](requirements.txt) and [INSTALL.txt](INSTALL.txt) for full details.

- Python 3.10+
- DIgSILENT PowerFactory 2023 or later (with Python interface enabled)
- fastmcp >= 2.0
- numpy >= 1.26
- matplotlib >= 3.8
- pandas >= 1.5

---

## Quick Start

1. Install Python dependencies: `pip install -r requirements.txt`
2. Add the PowerFactory Python path to your environment (see [INSTALL.txt](INSTALL.txt)).
3. Copy and edit the config: `cp simulation_config.example.json simulation_config.json`
4. Start the MCP server: `python MCP_PowerFactory.py`
5. Connect your AI assistant to the server using the MCP protocol.

---

## Prompt Examples

Below are example prompts you can send to an AI assistant connected to this MCP server.

**Health check**
```
Ping the PowerFactory server and confirm it's reachable.
```

**Run a load flow**
```
Run a load flow on the active study case and tell me if it converged.
```

**Run a transient fault simulation**
```
Simulate a three-phase bus fault on Bus 25 starting at t=1.0 s, cleared at t=1.08 s,
with a total simulation window of 10 s and a time step of 0.01 s. Export the results
and generate the voltage and generator speed plots.
```

**Modify a parameter before running**
```
Set the generator G 01.ElmSym out of service (e:outserv = 1),
then run a load flow and report the result.
```

**Create a new study case and run a custom fault**
```
Create a study case called "Scenario_A" based on "0. Base",
then run a line fault on "Line 12-34.ElmLne" from t=0.5 s to t=0.58 s
in a 15 s window. Save the CSV and plots to C:\Results\Scenario_A.
```

**Short-circuit calculation**
```
Run a short-circuit calculation on the active study case and return the results.
```

**Read the latest results**
```
Read the most recent RMS results CSV and summarise the peak voltage deviations
and minimum generator speed recorded during the simulation.
```

**Import a project and run the full pipeline**
```
Import the project at C:\Projects\IEEE39.pfd, activate it,
then run the full simulation pipeline defined in the config file.
```

---

## License

MIT
