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
Output folder:  CSV results, PNG plots, optional .pfd export
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
- **Grid diagram export** — export a selected active-project single-line diagram to PDF.
- **Greenfield equipment types** — create paper-backed transformer, overhead-line, and underground-cable types without requiring project templates.
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
| `get_parameters` | Reads selected attributes from matching calculation-relevant objects, with opt-in metadata and active-project library inspection. |
| `list_objects` | Lists calculation-relevant objects using a raw PowerFactory query. |
| `list_components` | Lists objects using friendly equipment categories. |
| `list_study_cases` | Lists study cases and identifies the active case. |
| `list_contingencies` | Lists configured fault-library cases and their `EvtOutage`, `EvtSwitch`, and `EvtShc` events without modifying the project. |
| `create_contingency` | Creates or reuses an idempotent switch-based contingency definition. |
| `get_contingency_configuration` | Reads the active Contingency Analysis command settings without running a calculation. |
| `configure_contingency_screening` | Persists selected DC/AC-linearised screening criteria without running a calculation. |
| `add_contingency_result_variables` | Adds variables to the configured AC or DC contingency result recording selection without running a calculation. |
| `remove_contingency_result_variables` | Removes variables from matching AC or DC result recording selections without running a calculation. |
| `export_active_grid_pdf` | Exports one active-project single-line diagram to a new PDF file. |
| `create_evemtbench_component` | Routes one nested parameter object to any validated EvEMTBench component creator. |
| `list_evemtbench_components` | Reads the versioned EvEMTBench transformer database without opening PowerFactory. |
| `create_evemtbench_transformer` | Previews or creates a new database-backed `TypTr2` and connected `ElmTr2` without a template. |
| `list_evemtbench_line_profiles` | Reads the versioned 20/110/345 kV overhead-line sequence profiles without opening PowerFactory. |
| `create_evemtbench_line` | Previews or creates a new profile-backed `TypLne` and connected `ElmLne` without a template. |
| `list_evemtbench_cable_profiles` | Reads the versioned 20 kV underground-cable sequence profiles without opening PowerFactory. |
| `create_evemtbench_cable` | Previews or creates a new Table 6 cable-equivalent `TypLne` and connected `ElmLne`. |
| `list_evemtbench_external_grid_profiles` | Reads the versioned EvEMTBench Table 4 external-grid ranges without opening PowerFactory. |
| `create_evemtbench_external_grid` | Previews or creates a seeded Table 4 `ElmXnet` on an existing bus. |
| `list_evemtbench_load_profiles` | Reads the versioned EvEMTBench Table 5 load-power ranges without opening PowerFactory. |
| `create_evemtbench_load` | Previews or creates a seeded Table 5 `ElmLod` on an existing bus. |
| `list_evemtbench_synchronous_machine_profiles` | Reads the versioned EvEMTBench Table 13 synchronous-machine ranges without opening PowerFactory. |
| `create_evemtbench_synchronous_machine` | Previews or creates a seeded round-rotor `TypSym` and connected `ElmSym`. |
| `create_grid_with_buses` | Previews or bootstraps an `ElmNet` and initial `ElmTerm` objects in the active project. |
| `import_project` | Imports a `.pfd` project file and activates it. |
| `create_study_case` | Creates (or activates) a study case by name, copying from a base case when needed. Supports `request_id` for idempotency. |
| `modify_parameter` | Sets one attribute on all PowerFactory objects matching a query string. Auto-casts string values to the correct type. |
| `add_component` | Creates a bus, load, generator, line, or two-winding transformer with validation, rollback, circuit breakers, and optional diagram insertion. |
| `delete_component` | Previews or confirms exact-name component deletion, including generated cubicles, circuit breakers, and optional diagram cleanup. |
| `run_loadflow` | Runs a standalone load flow calculation (ComLdf). |
| `run_short_circuit` | Runs a standalone short-circuit calculation (ComShc). |
| `run_contingency_analysis` | Runs ComSimoutage using its configured method or an explicit AC, DC, AC-linearised, or linearised-screening mode. |
| `get_contingency_results` | Reads a bounded, optionally variable-filtered slice of the configured AC or DC contingency result file using bulk or sparse access. |
| `get_contingency_summary` | Interprets existing contingency results as affected elements, convergence, overloads, and voltage violations. |
| `run_simulation` | Executes the full pipeline defined in `simulation_config.json`. |
| `run_custom_case` | Runs one fault simulation with parameters supplied at call time (no config file edit required). |
| `read_results_csv` | Reads an RMS result CSV; auto-discovers the latest file if no path is given. |

The contingency tools can create switch-based definitions and inspect or run
the active `ComSimoutage` command. An explicit calculation mode applies only to
that run; the study case's previous mode is restored afterward.

Read-only contingency tools search the active study case for an existing
`ComSimoutage`; they do not call `GetFromStudyCase`, which can create a missing
command. `get_contingency_results` accepts exact variable identifiers such as
`["c:loading"]`, returns each column's original index and object name/class when
PowerFactory provides one, and automatically includes `b:i_obj` for row-to-case
mapping. It uses `ElmRes.GetColumnValues` with a temporary, deleted `IntVec`,
falling back to PowerFactory's sparse iterator. Filtered reads resolve columns
from `IntMon` selections and `FindColumn`, avoiding a full `ElmRes` metadata
scan. `max_read_seconds` supplies a cooperative read budget; narrow `variables`,
`max_rows`, or `max_columns` for large files.

`configure_contingency_screening` intentionally persists selected screening
settings. It can choose DC or AC-linearised screening; enable the simple and
combined loading criteria; set their loading and relative-change thresholds;
ignore components already overloaded in the base case; and restrict screening
to recorded elements. It returns the previous and resulting settings without
executing the analysis.

Result recording is read from `IntMon` selections, never from stale result
columns. Both recording tools report each unreadable monitor once and keep
the record of successful changes to other objects. Class selections identified
by `IntMon.className` count as recorded for objects of that exact class.
Object-specific removal of a class-recorded variable is reported as failed,
without changing either its class or object selections. Other variables can
still be removed. Unidentified targetless selections remain errors; additions
and absence claims are skipped when their state is unknown.

Removal reports `failed_variables` separately from `already_absent_variables`.
A variable can appear in both `removed` and `failed` when different monitors
produce a partial change; rerun the analysis whenever `removed_variables` is
non-zero. `configured_objects` counts objects with readable matching selections,
and `objects_without_selection` counts objects with no known selection.
The tool schemas require strings; blank or whitespace-only variables are also
rejected. Missing screening flags are returned as `null`, rather than disabled.

PowerFactory 2026's User Manual, section 19.3.1.1, explicitly supports class-name
variable selections for contingency analysis. These tools report them rather
than attempting to remove a class-wide variable for an individual object.
Its Python Reference, section 5.6.26, documents `IntMon.RemoveVar` return codes:
`0` means removed, `1` means not found; other codes or exceptions are failures.

### Simulation Engine (`Agent_DIgSILENT.py`)

| Class / Method | Description |
|----------------|-------------|
| `SimulationConfig` | Dataclass holding all simulation parameters. `from_json()` loads from a JSON file. |
| `Logger` | Timestamped console logging with `info`, `ok`, `warn`, `error`, `section`. |
| `DIgSILENTAgent.__init__` | Initialises the agent from a `SimulationConfig`. |
| `DIgSILENTAgent.connect` | Connects to PowerFactory and activates the configured project. |
| `DIgSILENTAgent.activate_study_case` | Activates or creates the target study case. |
| `DIgSILENTAgent.run_loadflow` | Executes ComLdf. |
| `DIgSILENTAgent.run_contingency_analysis` | Executes ComSimoutage without changing its contingency filters and optionally selects a validated calculation mode. |
| `DIgSILENTAgent.run_rms_simulation` | Applies fault events, then runs ComInc + ComSim. |
| `DIgSILENTAgent._apply_fault_event` | Builds the event sequence for bus faults, line faults, or generator switches. |
| `DIgSILENTAgent.addSwitchEvent` | Creates a PowerFactory `EvtSwitch` event. |
| `DIgSILENTAgent.export_results_to_csv` | Exports the RMS result object to CSV via ComRes. |
| `DIgSILENTAgent.export_active_grid_pdf` | Exports a selected Graphics Board single-line diagram to PDF via ComWr. |
| `DIgSILENTAgent.create_evemtbench_component` | Validates and routes a unified request to an existing specialized component creator. |
| `DIgSILENTAgent.list_evemtbench_components` | Validates and filters the versioned transformer database. |
| `DIgSILENTAgent.create_evemtbench_transformer` | Samples, previews, creates, connects, verifies, and rolls back a new transformer type and element. |
| `DIgSILENTAgent.list_evemtbench_line_profiles` | Validates and filters the versioned overhead-line sequence profiles. |
| `DIgSILENTAgent.create_evemtbench_line` | Previews, creates, connects, verifies, and rolls back a new overhead-line type and element. |
| `DIgSILENTAgent.list_evemtbench_cable_profiles` | Validates and filters the versioned underground-cable sequence profiles. |
| `DIgSILENTAgent.create_evemtbench_cable` | Previews, creates, connects, verifies, and rolls back a new cable type and element. |
| `DIgSILENTAgent.list_evemtbench_external_grid_profiles` | Validates and filters the external-grid catalog. |
| `DIgSILENTAgent.create_evemtbench_external_grid` | Samples, previews, creates, connects, verifies, and rolls back a new external grid. |
| `DIgSILENTAgent.create_grid_with_buses` | Previews, creates or reuses, verifies, and rolls back a grid and its initial buses. |
| `DIgSILENTAgent.export_project_to_pfd` | Exports the active project to `.pfd` via ComPfdexport. |
| `DIgSILENTAgent.generate_standard_plots` | Reads the exported CSV and produces voltage and generator speed PNG plots. |
| `DIgSILENTAgent.import_project` | Imports a `.pfd` file into the running PowerFactory session. |
| `DIgSILENTAgent.create_study_case` | Creates or reuses a study case by exact name. |
| `DIgSILENTAgent.modify_parameter` | Sets an attribute on all objects returned by `GetCalcRelevantObjects`. |
| `DIgSILENTAgent.add_component` | Creates and verifies supported network components and their connections. |
| `DIgSILENTAgent.delete_component` | Performs guarded exact-name component deletion and cleanup. |
| `DIgSILENTAgent.short_circuit` | Standalone ComShc execution. |
| `DIgSILENTAgent.run_pipeline` | Orchestrates the full workflow and returns a structured status report. |
| `DIgSILENTAgent.close` | Shuts down PowerFactory and clears shared handles. |

## Greenfield Grid Bootstrap

`create_grid_with_buses` removes the requirement for a pre-existing
calculation grid and buses. It requires an active PowerFactory project and
study case. It can create the standard `Network Model` / `Network Data` folder
hierarchy, a new `ElmNet`, and one to 100 `ElmTerm` objects without using a
template. A confirmed call activates the grid and verifies that PowerFactory
reports it as calculation-relevant.

```text
create_grid_with_buses(
    grid_name="Research Grid",
    nominal_frequency_hz=50,
    buses=[
        {"name": "HV Bus", "nominal_voltage_kv": 110},
        {
            "name": "MV Bus",
            "nominal_voltage_kv": 20,
            "out_of_service": true
        }
    ],
    confirmation=""
)
```

The first call is a read-only preview. Repeat it with the exact returned
`confirmation_required` value to apply the plan. An existing grid or bus is
reused only when its frequency, voltage, and service state match exactly;
conflicting objects are reported without modification. If creation fails, all
objects created by that call are removed. The tool does not create a project,
study case, single-line diagram, equipment type, or calculation command.

The bootstrap currently accepts 50 or 60 Hz so its grid is compatible with the
EvEMTBench transformer and overhead-line creators. Once the buses exist, pass
their names and the grid name directly to those tools.

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

Component names are limited to 40 characters, matching PowerFactory's
`loc_name` limit.

An explicit `null` for optional reactive power is treated as an omitted value
and defaults to zero. Boolean values are not accepted for numeric parameters.

Each generated connection cubicle contains one closed circuit breaker
(`StaSwitch`, `aUsage="cbk"`, `on_off=1`). Set `update_graphics=true` to
request insertion into the active single-line diagram.

Graphical updates use the Diagram Layout Tool's automatic insertion mode so
existing diagram objects are not re-laid out as a K-neighbourhood.

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
DELETE <component_type> <full PowerFactory object path>
```

Name lookup is case-insensitive. The confirmation phrase contains the full
PowerFactory object path, binds the confirmation to the previewed grid, and
must be copied exactly from the preview.

Confirmed deletion removes the exact component. A connection cubicle is removed
only when its generated name and sole generated circuit breaker both match;
cubicles containing relays, instrument transformers, or other objects are
preserved. A bus cannot be deleted while it still has connected cubicles. Set
`update_graphics=true` to remove matching diagram objects from every single-line
diagram in the active project and rebuild the active view.

The response reports component deletion separately from cleanup. In particular,
`success=false` with `deleted=true` means the network component was removed but
some graphical or cubicle cleanup failed; do not retry the component deletion.

---

## Unified EvEMTBench Component Creator

`create_evemtbench_component` is the common write entry point for the six
validated component families: `transformer`, `overhead_line`,
`underground_cable`, `external_grid`, `load`, and `synchronous_machine`.
Supply the selected specialized creator's arguments inside `parameters`:

```python
create_evemtbench_component(
    component_type="load",
    parameters={
        "voltage_kv": 20,
        "load_name": "Research Load",
        "bus_name": "MV Bus",
        "grid_name": "Research Grid",
        "seed": 42,
        "out_of_service": True,
        "confirmation": "",
        "open_digsilent": True,
    },
)
```

An empty `confirmation` keeps the request in preview mode. Repeat the same
request with the exact returned `confirmation_required` value to apply it.
The unified tool delegates validation, seeded sampling, creation, retained-value
checks, and rollback to the existing specialized creator without changing its
behavior. The specialized tools remain available for backward compatibility
and for clients that benefit from their explicit per-component schemas.

---

## EvEMTBench Transformer Database and Creator

The versioned database at
[`data/evemtbench_transformers.json`](data/evemtbench_transformers.json)
stores the fixed-voltage transformer classes from EvEMTBench Tables 10-12.
Use `list_evemtbench_components` to inspect classes, ratings, ranges, vector
groups, zero-sequence rules, and saturation data without opening PowerFactory.

`create_evemtbench_transformer` creates a new `TypTr2` directly; it does not
copy or require an existing transformer. It also creates an `ElmTr2`, two
cubicles, and closed circuit breakers between existing buses. The type is
stored in the project library's `Transformer Types` folder; a confirmed call
creates that folder when it is absent from a greenfield project. The first
call is a read-only preview when `confirmation` is empty:

```text
create_evemtbench_transformer(
    voltage_class="110/20",
    rated_power_mva=20,
    nominal_frequency_hz=60,
    vector_group="YNd",
    clock_number=11,
    transformer_name="Research Transformer",
    type_name="Research Transformer Type",
    high_voltage_bus_name="HV Bus",
    low_voltage_bus_name="LV Bus",
    seed=42,
    confirmation="",
    open_digsilent=true
)
```

The preview validates the grid, buses, nominal voltages, names, rating, vector
group, clock number, and an explicit nominal frequency of 50 or 60 Hz, then
returns the exact confirmation phrase. Frequency is not inferred from the grid
because existing projects can contain types with a different `frnom`. A
confirmed call writes three-phase technology (`nt2ph`), frequency (`frnom`),
the impedance modes, `strn`, `utrn_h`, `utrn_l`, `uktr`, `pcutr`, `pfe`,
`curmg`, `tr2cn_h`, `tr2cn_l`, and `nt2ag`. Structural settings and nameplate
ratings are committed before the performance values so PowerFactory can
refresh dependent type fields. Copper loss and short-circuit voltage are
converted to the equivalent `r1pu` and `x1pu` values before assignment, then
verified again through PowerFactory's derived `pcutr` and `uktr` attributes.
The performance values use PowerFactory's native Python property assignment;
each value is checked immediately and again after the database write. If element
creation fails, the new type, element, cubicles, and switches are rolled back.

Table 10 zero-sequence and Table 12 saturation data are stored and returned by
the catalog tool, but are not written until their PowerFactory attribute
mappings are validated. The `Block` class and other component families remain
catalog-only for the same reason. The caller must explicitly choose a clock
number because Table 11 specifies vector-group families rather than one clock
number for every generated transformer.

See [references/evemtbench.md](references/evemtbench.md) for the source mapping
and limitations.

---

## EvEMTBench Overhead-Line Database and Creator

[`data/evemtbench_overhead_lines.json`](data/evemtbench_overhead_lines.json)
stores the published 5th, 50th and 95th percentile sequence parameters from
Table 7 for 20, 110 and 345 kV overhead lines, together with the corresponding
Table 3 length ranges. `list_evemtbench_line_profiles` inspects this catalog
without opening PowerFactory.

`create_evemtbench_line` creates a new `TypLne` directly and connects a new
`ElmLne` between two existing equal-voltage buses. The caller selects `p05`,
`p50` or `p95`, supplies the actual current rating, and chooses 50 or 60 Hz.
The first call is a read-only preview:

```text
create_evemtbench_line(
    voltage_kv=110,
    nominal_frequency_hz=50,
    rated_current_ka=1,
    profile="p50",
    length_km=10,
    line_name="Research Line",
    type_name="Research Line Type",
    bus1_name="Bus A",
    bus2_name="Bus B",
    confirmation="",
    open_digsilent=true
)
```

The preview checks the voltage class, frequency, paper length range, existing
buses, names, and exact confirmation phrase. A confirmed call creates the
project library's `Line Types` folder when needed, writes `uline`, `sline`,
`frnom`, `rline`, `xline`, `cline`, `rline0`, `xline0` and `cline0`, and then
creates the line, two cubicles and closed circuit breakers. Published
capacitances are converted from nF/km to PowerFactory's uF/km attributes. New
objects are rolled back when creation fails.

This tool deliberately implements a three-phase `TypLne` sequence equivalent,
not the paper's frequency-dependent geometric ULM model. The three published
percentiles are discrete profiles rather than endpoints of an invented
sampling distribution. Tower and conductor geometry remains catalog-only.

---

## EvEMTBench Underground-Cable Database and Creator

[`data/evemtbench_underground_cables.json`](data/evemtbench_underground_cables.json)
stores Table 6's published 5th, 50th and 95th percentile sequence parameters
for 20 kV underground cables and Table 3's 0.5 to 3.75 km length range.
`list_evemtbench_cable_profiles` returns those profiles plus the paper's
construction and installation data without opening PowerFactory.

`create_evemtbench_cable` creates a new `TypLne` sequence equivalent and
connects a new `ElmLne` between two existing 20 kV buses. The caller chooses a
published percentile, 50 or 60 Hz, and an engineering current rating because
Table 6 does not publish cable ampacity. The first call is a read-only preview:

```text
create_evemtbench_cable(
    nominal_frequency_hz=50,
    rated_current_ka=0.4,
    profile="p50",
    length_km=2,
    cable_name="Research Cable",
    type_name="Research Cable Type",
    bus1_name="MV Bus A",
    bus2_name="MV Bus B",
    grid_name="Research Grid",
    out_of_service=true,
    confirmation="",
    open_digsilent=true
)
```

Repeat the call with the exact returned `confirmation_required` value to
create the type, cable element, two cubicles, and closed circuit breakers.
Published capacitances are converted from nF/km to PowerFactory's uF/km
attributes, retained values are verified, and new objects are rolled back if
creation fails.

The created `TypLne` is a three-phase sequence equivalent suitable for initial
network construction; it is not the paper's geometric ULM cable model. The
catalog preserves insulation, conductor, sheath, arrangement, burial-depth,
spacing, and earth-resistivity data for a future geometric implementation.

---

## EvEMTBench External-Grid Database and Creator

[`data/evemtbench_external_grids.json`](data/evemtbench_external_grids.json)
stores the Table 4 ranges for 110 kV and combined 380/345 kV external-grid
equivalents. `list_evemtbench_external_grid_profiles` inspects the ranges
without opening PowerFactory.

`create_evemtbench_external_grid` uses a supplied seed to sample every Table 4
interval uniformly and connects a new slack `ElmXnet` to an existing bus. The
bus must be exactly 110, 345, or 380 kV. The first call is a read-only preview:

```text
create_evemtbench_external_grid(
    voltage_kv=110,
    external_grid_name="Research External Grid",
    bus_name="HV Bus",
    grid_name="Research Grid",
    seed=42,
    out_of_service=true,
    confirmation="",
    open_digsilent=true
)
```

Repeat the call with the exact returned `confirmation_required` value to create
the external grid, cubicle, and closed circuit breaker. The tool writes `snss`,
`rntxn`, `x0tx1`, `r0tx0`, `usetp`, and `phiini`, sets `bustp="SL"`, verifies
the retained values, and rolls back new objects if creation fails. The sampled
values are research inputs and must still be checked for suitability in the
target network. The attribute mapping and retained values were validated on
PowerFactory 2026 SP1; SP4 validation remains pending.

---

## EvEMTBench Load Database and Creator

[`data/evemtbench_loads.json`](data/evemtbench_loads.json) stores the Table 5
load-power ranges for 20, 110, and 345 kV systems. The read-only
`list_evemtbench_load_profiles` tool returns these ranges without opening
PowerFactory.

`create_evemtbench_load` samples active and reactive power directly at 110 and
345 kV. At 20 kV it samples apparent power and a reactive-power angle between
the published 0.95 capacitive and 0.8 inductive limits, then calculates P and
Q. The first call is a read-only preview:

```text
create_evemtbench_load(
    voltage_kv=20,
    load_name="Research Load",
    bus_name="MV Bus",
    grid_name="Research Grid",
    seed=42,
    out_of_service=true,
    confirmation="",
    open_digsilent=true
)
```

Repeat the call with the exact returned `confirmation_required` value to create
the balanced `ElmLod`, cubicle, and closed circuit breaker. The tool verifies
`plini`, `qlini`, the bus connection, and the service state and rolls back new
objects if creation fails. The Table 5 ZIP coefficients remain catalog-only
until their PowerFactory attribute mapping is live-validated.

---

## EvEMTBench Synchronous-Machine Database and Creator

[`data/evemtbench_synchronous_machines.json`](data/evemtbench_synchronous_machines.json)
stores the salient-pole and round-rotor ranges from Table 13, including the
rated-voltage selection rule and parameter dependencies. Use
`list_evemtbench_synchronous_machine_profiles` to inspect both profiles or to
filter by `salient_pole` or `round_rotor`.

`create_evemtbench_synchronous_machine` supports the round-rotor profile. The
caller selects a rating from 25 to 1200 MVA and an existing bus. The tool
derives the rated voltage using Table 13 (6.3, 10.5, 21, or 27 kV), samples the
remaining ranges reproducibly from `seed`, and validates all published
reactance and saturation dependencies. The requested P/Q operating point must
fit the MVA rating and the paper's reactive-power limits.

```python
create_evemtbench_synchronous_machine(
    machine_type="round_rotor",
    rated_power_mva=100,
    machine_name="Research Generator",
    type_name="Research Generator Type",
    bus_name="Generator Bus 10.5",
    grid_name="Research Grid",
    seed=42,
    active_power_mw=60,
    reactive_power_mvar=5,
    out_of_service=true,
    confirmation="",
    open_digsilent=true
)
```

Repeat the call with the exact returned `confirmation_required` string to
create the `TypSym`, `ElmSym`, cubicle, and closed circuit breaker. The type is
created without a template, and all new objects are rolled back if creation
fails. Table 13's short-circuit time constants are converted to PowerFactory's
writable open-circuit inputs and checked again through the derived `tds`,
`tqs`, `tdss`, and `tqss` values. The attribute relationships, `iturbo=1`
round-rotor mode, confirmed creation, and structured response were validated
on PowerFactory 2026 SP1. Salient-pole creation remains disabled because Table
13 does not provide `x'q` or `T'q`; the profile continues to be available
through the read-only catalog.

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

**Export an active grid diagram to PDF**
```
Export the single-line diagram named "Summary Grid" from the active
PowerFactory project to C:\Projects\exports\summary-grid.pdf.
Do not overwrite an existing file.
```

**Inspect and preview an EvEMTBench transformer**
```
List the available 110/20 kV EvEMTBench transformer ratings. Then preview a
20 MVA YNd11 transformer type named "Research Transformer Type" and an element
named "Research Transformer" between "HV Bus" and "LV Bus", using seed 42.
Return the sampled values and confirmation phrase without creating anything.
```

---

## Research provenance and affiliation

PowerFactory development and validation contributions by Aswin Krishna Poyil
are carried out at the **Institute of Electrical Energy Systems,
Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU)** under the
supervision of Tobias Lorz and Timon Conrad, whose support provided the
opportunity to pursue this work independently.

The transformer-type library generator is informed by Georg Kordowich,
Jonathan Loebel, Julian Oelhaf, Andreas Maier, Siming Bayer, Christian Bergler,
and Johann Jaeger, *A simulation based dataset of faults and events for machine
learning in power systems*, arXiv:2608.19777 (2026). The paper documents the
EvEMTBench element models and parameter ranges used to construct realistic
synthetic grids. See [references/evemtbench.md](references/evemtbench.md) for
the implementation notes and source links.

---

## License

MIT

## Automated tests and validation reports

Run the PowerFactory unit and catalog tests from the repository root:

```powershell
python -m pytest PowerFactory/tests -q
```

The installed-wheel smoke test, `tests/check_evemtbench_wheel.py`, runs separately
in CI against an installed package outside the checkout.
Validation records and the contribution and function-test reports are in
[`evidence/`](evidence/README.md).
