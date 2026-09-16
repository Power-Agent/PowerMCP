# DIgSILENT PowerFactory MCP Agent

A Model Context Protocol (MCP) server that exposes DIgSILENT PowerFactory simulation capabilities to AI assistants such as Claude. The agent automates RMS transient stability simulations, load flow and short-circuit calculations, parameter modifications, and result exports — all through a clean, tool-callable interface.

---

## Architecture

```
Claude / AI assistant
        │  MCP protocol
        ▼
MCP_PowerFactory.py   ← MCP Python SDK 2 server
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

## Features

- **Full simulation pipeline** — connect, activate study case, load flow, RMS transient simulation, CSV export, plot generation, optional PFD export in one call.
- **Custom fault scenarios** — define bus faults, line faults, and generator switching events at call time without editing config files.
- **Parameter modification** — update any PowerFactory attribute on any object via the MCP interface.
- **Model inspection and discovery** — inspect the active project and study case, read selected attributes, and discover objects using raw queries or friendly component categories.
- **Guarded component management** — create or safely preview and delete buses, loads, generators, lines, and two-winding transformers.
- **Diagram and switchgear synchronization** — optionally update the active single-line diagram and create one closed circuit breaker in each generated connection cubicle.
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
| `get_active_project` | Returns the active PowerFactory project without modifying it. |
| `get_active_study_case` | Returns the active PowerFactory study case without modifying it. |
| `get_parameters` | Reads selected attributes from objects matching a PowerFactory query. |
| `list_objects` | Lists calculation-relevant objects using a raw PowerFactory query. |
| `list_components` | Lists objects using friendly equipment categories. |
| `list_study_cases` | Lists study cases and identifies the active case. |
| `import_project` | Imports a `.pfd` project file and activates it. |
| `create_study_case` | Creates (or activates) a study case by name, copying from a base case when needed. Supports `request_id` for idempotency. |
| `modify_parameter` | Sets one attribute on all PowerFactory objects matching a query string. Auto-casts string values to the correct type. |
| `add_component` | Creates a bus, load, generator, line, or two-winding transformer with validation, rollback, circuit breakers, and optional diagram insertion. |
| `delete_component` | Previews or confirms exact-name component deletion, including generated cubicles, circuit breakers, and optional diagram cleanup. |
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
| `DIgSILENTAgent.get_active_project` | Returns the active project identity. |
| `DIgSILENTAgent.get_active_study_case` | Returns the active study-case identity. |
| `DIgSILENTAgent.get_parameters` | Reads selected object attributes. |
| `DIgSILENTAgent.list_objects` | Lists objects using a PowerFactory query. |
| `DIgSILENTAgent.list_components` | Lists friendly component categories. |
| `DIgSILENTAgent.list_study_cases` | Lists available study cases and marks the active one. |
| `DIgSILENTAgent.add_component` | Creates and verifies supported network components and their connections. |
| `DIgSILENTAgent.delete_component` | Performs guarded exact-name component deletion and cleanup. |
| `DIgSILENTAgent.short_circuit` | Standalone ComShc execution. |
| `DIgSILENTAgent.run_pipeline` | Orchestrates the full workflow and returns a structured status report. |
| `DIgSILENTAgent.close` | Shuts down PowerFactory and clears shared handles. |

## Component Management

### Create a component

```text
add_component(
    component_type,
    component_name,
    parameters,
    grid_name="",
    out_of_service=false,
    open_digsilent=true,
    update_graphics=false
)
```

Supported component parameters:

| Type | Required parameters | Optional parameters |
|---|---|---|
| `bus` | `nominal_voltage_kv` | — |
| `load` | `bus_name`, `active_power_mw` | `reactive_power_mvar` |
| `generator` | `bus_name`, `template_generator`, `active_power_mw` | `reactive_power_mvar` |
| `line` | `bus1_name`, `bus2_name`, `template_line`, `length_km` | — |
| `transformer` | `high_voltage_bus_name`, `low_voltage_bus_name`, `template_transformer` | — |

Each generated connection cubicle contains one closed circuit breaker
(`StaSwitch`, `aUsage="cbk"`, `on_off=1`). Set `update_graphics=true` to
request insertion into the active single-line diagram.

If graphical insertion fails, the network component remains created and the
tool returns `success=false` with the graphical error. Check the returned
message before retrying to avoid creating a duplicate.

PowerFactory may place an isolated bus far from the existing network when it
is inserted directly into the diagram. For a better anchored result, create
the bus with `update_graphics=false`, then create its first connecting line
with `update_graphics=true`.

### Delete a component

```text
delete_component(
    component_type,
    component_name,
    grid_name="",
    confirmation="",
    open_digsilent=true,
    update_graphics=false
)
```

Calling `delete_component` without confirmation returns a preview and the
required confirmation phrase:

```text
DELETE <component_type> <exact component name>
```

Confirmed deletion removes the exact component and its generated cubicles and
circuit breakers. A bus cannot be deleted while it still has connected
cubicles. Set `update_graphics=true` to remove the corresponding diagram object
and rebuild the active view.

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
- PowerFactory Python module path configured through `POWERFACTORY_PYTHON_PATH` or `PYTHONPATH`
- MCP Python SDK 2.x
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

**Inspect the active context**
```
Return the active PowerFactory project and study case, then list the first ten
buses without modifying anything.
```

**Create and connect a bus**
```
Create an in-service 110 kV bus named "MCP Example Bus" in Grid without a
graphical update. Connect Bus 01 to it with a 1 km line based on
"Line 01 - 02.ElmLne", request a graphical update for the line, and run a load
flow. Stop if any operation fails.
```

**Preview and delete a component**
```
Preview deletion of the load "MCP Example Load" in Grid. Show me the required
confirmation phrase and do not perform the confirmed deletion yet.
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
