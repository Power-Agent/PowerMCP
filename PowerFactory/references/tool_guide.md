# PowerFactory tool and workflow guide

[Back to the README](../README.md)

Detailed tool inventories, equipment examples, configuration, and validation notes.

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
| `list_evemtbench_components` | Lists any of six EvEMTBench catalogs, filters and required creation parameters without opening PowerFactory. |
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
| `DIgSILENTAgent.list_evemtbench_components` | Routes catalog requests for all six types and returns parameter metadata. |
| `DIgSILENTAgent.list_evemtbench_transformer_profiles` | Internal transformer catalog implementation. |
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
Use the creation inputs returned by `list_evemtbench_components` inside
`parameters`:

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

For all six component types, `out_of_service` and `open_digsilent` require
actual JSON booleans (`true` or `false`; `True` or `False` in Python).
Strings such as `"false"`, numbers such as `0` or `1`, and `null` are rejected
before connecting to PowerFactory. Omit either option to use its documented
default.
The unified tool delegates validation, seeded sampling, creation, retained-value
checks, and rollback to the existing specialized creator without changing its
behavior. Only the unified create and list tools are exposed through MCP.
Specialized methods remain internal Python implementation details.

### Catalog discovery and migration

Call `list_evemtbench_components(component_type, filters)` before creating equipment.
Omit `filters` to inspect the complete selected catalog. The response includes
`available_filters` and `creation_parameters`, with names, types, required flags,
and defaults. Catalog-only data and mapping limits remain in the response.

| component_type | Optional filters |
|---|---|
| `transformer` | `voltage_class`, `rated_power_mva` (requires voltage_class) |
| `overhead_line` | `voltage_kv`, `profile` |
| `underground_cable` | `profile` |
| `external_grid` | `voltage_kv` |
| `load` | `voltage_kv` |
| `synchronous_machine` | `machine_type` |

```python
list_evemtbench_components(
    component_type="overhead_line",
    filters={"voltage_kv": 110, "profile": "p50"},
)
```

This intentionally changes the MCP interface. Replace previous specialized
create calls with `create_evemtbench_component` and place their arguments inside
`parameters`. Replace specialized list calls with `list_evemtbench_components`
and place their filters inside `filters`. The old transformer-only listing now
requires `component_type="transformer"`; move voltage_class/rated_power_mva into
`filters`. Restart the server and refresh the client's tool list after updating.
The examples below use the new public interface.

---

## EvEMTBench Transformer Database and Creator

The versioned database at
[`data/evemtbench_transformers.json`](../data/evemtbench_transformers.json)
stores the fixed-voltage transformer classes from EvEMTBench Tables 10-12.
Use `list_evemtbench_components` to inspect classes, ratings, ranges, vector
groups, zero-sequence rules, and saturation data without opening PowerFactory.

`create_evemtbench_component(component_type="transformer", parameters=...)` creates a new `TypTr2` directly; it does not
copy or require an existing transformer. It also creates an `ElmTr2`, two
cubicles, and closed circuit breakers between existing buses. The type is
stored in the project library's `Transformer Types` folder; a confirmed call
creates that folder when it is absent from a greenfield project. The first
call is a read-only preview when `confirmation` is empty:

```text
create_evemtbench_component(
    component_type="transformer",
    parameters={
        "voltage_class": "110/20",
        "rated_power_mva": 20,
        "nominal_frequency_hz": 60,
        "vector_group": "YNd",
        "clock_number": 11,
        "transformer_name": "Research Transformer",
        "type_name": "Research Transformer Type",
        "high_voltage_bus_name": "HV Bus",
        "low_voltage_bus_name": "LV Bus",
        "seed": 42,
        "confirmation": "",
        "open_digsilent": True,
    },
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

Full Table 10 core/limb and Table 12 saturation mappings remain unsupported.
The restricted zero-sequence equivalent below is an opt-in exception. The
`Block` class remains catalog-only. The caller must explicitly choose a clock
number because Table 11 specifies vector-group families rather than one clock
number for every generated transformer.

See [references/evemtbench.md](evemtbench.md) for the source mapping
and limitations.

### Opt-in YNd11 zero-sequence impedance equivalent

For **20 MVA, 110/20 kV, 60 Hz, YNd11 only**, add these fields to the
transformer creation `parameters` (not a complete creation request):

```json
{
    "zero_sequence_model": "ynd11_equivalent",
    "r0_r1_ratio": 2.15,
    "x0_x1_ratio": 0.925
}
```

The default `zero_sequence_model="unchanged"` preserves the previous creation
path; ratios are rejected unless the opt-in model is selected. The equivalent
requires finite numeric R0/R1 in [1.5, 2.8] and X0/X1 in [0.85, 1.0], taken
from Table 10's three-limb numerical rule. No physical three-limb/core model
is configured or claimed. Ratios are explicit engineering choices, not sampled.
Other ratings, classes, frequencies, vector groups and clock numbers are rejected.

The creator derives R1/X1 from the same sampled Table 11 data as before, then
writes `r0pu = r1pu * r0_r1_ratio` and `x0pu = x1pu * x0_x1_ratio`. It checks
derived `ur0tr` and `uk0tr`, and leaves positive-sequence data unchanged.
For the new element only, it explicitly sets `neutConfig=0`, `cgnd_h=0`,
`re0tr_h=0`, `xe0tr_h=0`: no external neutral conductor, connected HV star
point, zero internal neutral impedance. Existing elements are not edited.
Model, ratios, derived parameters, grounding and destination are confirmation-bound.
Type/connection failures roll back new objects; a type is retained if failed
element cleanup leaves a transformer behind, with survivors reported.

Lab PC write/readback and Complete Method sensitivity/I0-blocking checks passed
on a separate temporary network: [FT-30](../evidence/FT-30_transformer_zero_sequence_ynd_lab_pc.txt).
These do not validate absolute fault-current accuracy, core/limb construction,
zero-sequence magnetizing models, internal-delta YNyn cases, saturation or RMS/EMT.
The integrated opt-in creator also passed Lab PC creation and readback checks:
[FT-31](../evidence/FT-31_integrated_transformer_zero_sequence_creation_lab_pc.txt).
The new transformer remained out of service, with the requested type and solid
HV-neutral grounding retained. No calculation was run on that integrated
transformer; the fault-response checks used the separate FT-30 network.

[FT-32](../evidence/FT-32_transformer_earth_fault_reference_lab_pc.txt) adds an
independent absolute-current comparison for a separate unloaded, lossless YNd11
equivalent, including a source-only control and 20-ohm neutral-resistance case.
All four comparisons passed the predeclared 0.5% relative / 0.00001 kA absolute
tolerance; the record includes the complete JSON, script and rerun instructions.
This is not an absolute-current certification of the original lossy type or
integrated transformer, and does not extend the creator's configuration scope.

---

## EvEMTBench Overhead-Line Database and Creator

[`data/evemtbench_overhead_lines.json`](../data/evemtbench_overhead_lines.json)
stores the published 5th, 50th and 95th percentile sequence parameters from
Table 7 for 20, 110 and 345 kV overhead lines, together with the corresponding
Table 3 length ranges. `list_evemtbench_components(component_type="overhead_line")` inspects this catalog
without opening PowerFactory.

`create_evemtbench_component(component_type="overhead_line", parameters=...)` creates a new `TypLne` directly and connects a new
`ElmLne` between two existing equal-voltage buses. The caller selects `p05`,
`p50` or `p95`, supplies the actual current rating, and chooses 50 or 60 Hz.
The first call is a read-only preview:

```text
create_evemtbench_component(
    component_type="overhead_line",
    parameters={
        "voltage_kv": 110,
        "nominal_frequency_hz": 50,
        "rated_current_ka": 1,
        "profile": "p50",
        "length_km": 10,
        "line_name": "Research Line",
        "type_name": "Research Line Type",
        "bus1_name": "Bus A",
        "bus2_name": "Bus B",
        "confirmation": "",
        "open_digsilent": True,
    },
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

[`data/evemtbench_underground_cables.json`](../data/evemtbench_underground_cables.json)
stores Table 6's published 5th, 50th and 95th percentile sequence parameters
for 20 kV underground cables and Table 3's 0.5 to 3.75 km length range.
`list_evemtbench_components(component_type="underground_cable")` returns those profiles plus the paper's
construction and installation data without opening PowerFactory.

`create_evemtbench_component(component_type="underground_cable", parameters=...)` creates a new `TypLne` sequence equivalent and
connects a new `ElmLne` between two existing 20 kV buses. The caller chooses a
published percentile, 50 or 60 Hz, and an engineering current rating because
Table 6 does not publish cable ampacity. The first call is a read-only preview:

```text
create_evemtbench_component(
    component_type="underground_cable",
    parameters={
        "nominal_frequency_hz": 50,
        "rated_current_ka": 0.4,
        "profile": "p50",
        "length_km": 2,
        "cable_name": "Research Cable",
        "type_name": "Research Cable Type",
        "bus1_name": "MV Bus A",
        "bus2_name": "MV Bus B",
        "grid_name": "Research Grid",
        "out_of_service": True,
        "confirmation": "",
        "open_digsilent": True,
    },
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

[`data/evemtbench_external_grids.json`](../data/evemtbench_external_grids.json)
stores the Table 4 ranges for 110 kV and combined 380/345 kV external-grid
equivalents. `list_evemtbench_components(component_type="external_grid")` inspects the ranges
without opening PowerFactory.

`create_evemtbench_component(component_type="external_grid", parameters=...)` uses a supplied seed to sample every Table 4
interval uniformly and connects a new slack `ElmXnet` to an existing bus. The
bus must be exactly 110, 345, or 380 kV. The first call is a read-only preview:

```text
create_evemtbench_component(
    component_type="external_grid",
    parameters={
        "voltage_kv": 110,
        "external_grid_name": "Research External Grid",
        "bus_name": "HV Bus",
        "grid_name": "Research Grid",
        "seed": 42,
        "out_of_service": True,
        "confirmation": "",
        "open_digsilent": True,
    },
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

[`data/evemtbench_loads.json`](../data/evemtbench_loads.json) stores the Table 5
load-power ranges for 20, 110, and 345 kV systems. The read-only
`list_evemtbench_components(component_type="load")` tool returns these ranges without opening
PowerFactory.

`create_evemtbench_component(component_type="load", parameters=...)` samples active and reactive power directly at 110 and
345 kV. At 20 kV it samples apparent power and a reactive-power angle between
the published 0.95 capacitive and 0.8 inductive limits, then calculates P and
Q. The first call is a read-only preview:

```text
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

Repeat the call with the exact returned `confirmation_required` value to create
the balanced `ElmLod`, cubicle, and closed circuit breaker. The tool verifies
`plini`, `qlini`, the bus connection, and the service state and rolls back new
objects if creation fails. This remains the default `load_model="constant_power"`
path: no load type is created or assigned, and seeded P/Q values are unchanged.

### Opt-in ZIP load-flow model

Add `"load_model": "zip"` and an explicit, unused `"type_name"` to the load's
`parameters`. For example, add these to the preview above:

```json
{
    "load_model": "zip",
    "type_name": "Research ZIP Load Type"
}
```

These are additional parameters, not a complete request. Repeat the complete
preview request with its exact confirmation string to create a new `TypLod`
and connected `ElmLod`. Existing types are never reused or edited. The `Load
Types` folder is created only on confirmation if needed. Model, type name,
destination, coefficients, and exponents are bound into the confirmation plan.

For P and Q independently, a separate seeded stream samples Z uniformly over
its feasible interval, then I uniformly over its conditional feasible interval,
and derives P = 1 - Z - I. All coefficients stay in the published ranges,
including negative values. This is not independent uniform sampling of all six
terms, nor a claim to reproduce the paper's joint distribution.

`aP`/`aQ` receive constant-power coefficients, `bP`/`bQ` constant-current
coefficients, and PowerFactory derives `cP`/`cQ` for constant impedance.
Exponents are explicitly set to 0, 1, and 2. Writable and derived attributes
are verified after the database write. Failures roll back new objects;
incomplete cleanup is reported, and a type is preserved if failed load
cleanup leaves an element behind.

This maps **balanced steady-state load flow only**. Enable **Consider Voltage
Dependency of Loads** in `ComLdf` to use ZIP behavior. The creator does not
alter calculation settings, dynamic percentages, time constants, or voltage
limits. RMS/EMT behavior remains unvalidated. Supplying `type_name` in
constant-power mode is rejected rather than silently ignored.

The Lab PC mapping and separate diagnostic voltage-response checks are in
[FT-28](../evidence/FT-28_load_zip_mapping_lab_pc.txt). Integrated unified-tool
creation and retained-value verification of an out-of-service ZIP load passed
on the Lab PC; see [FT-29](../evidence/FT-29_integrated_zip_load_creation_lab_pc.txt).
No calculation was run on that integrated load. RMS/EMT validation remains pending.

---

## EvEMTBench Synchronous-Machine Database and Creator

[`data/evemtbench_synchronous_machines.json`](../data/evemtbench_synchronous_machines.json)
stores the salient-pole and round-rotor ranges from Table 13, including the
rated-voltage selection rule and parameter dependencies. Use
`list_evemtbench_components(component_type="synchronous_machine")` to inspect both profiles or to
filter by `salient_pole` or `round_rotor`.

`create_evemtbench_component(component_type="synchronous_machine", parameters=...)` supports the round-rotor profile. The
caller selects a rating from 25 to 1200 MVA and an existing bus. The tool
derives the rated voltage using Table 13 (6.3, 10.5, 21, or 27 kV), samples the
remaining ranges reproducibly from `seed`, and validates all published
reactance and saturation dependencies. The requested P/Q operating point must
fit the MVA rating and the paper's reactive-power limits.

```python
create_evemtbench_component(
    component_type="synchronous_machine",
    parameters={
        "machine_type": "round_rotor",
        "rated_power_mva": 100,
        "machine_name": "Research Generator",
        "type_name": "Research Generator Type",
        "bus_name": "Generator Bus 10.5",
        "grid_name": "Research Grid",
        "seed": 42,
        "active_power_mw": 60,
        "reactive_power_mvar": 5,
        "out_of_service": True,
        "confirmation": "",
        "open_digsilent": True,
    },
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

## Automated tests and validation reports

The EvEMTBench catalogs and builders are implemented in `evemtbench.py` and
inherited by `DIgSILENTAgent`. The public MCP interface now uses only
`list_evemtbench_components(component_type, filters)` and
`create_evemtbench_component(component_type, parameters)`; specialized MCP
tools have been removed. Existing clients must migrate and refresh their tool list.
Equipment-type rollback and confirmation hashing share helpers in that module.

Grid-bootstrap confirmation is bound to the active project and study case,
the resolved grid, the destination folder for a new grid, and the
create/reuse/activation decisions. The preview returns the destination folder
and required folder-creation decisions in `destination_plan`. If that state
changes, request a fresh preview before confirming, including for repeated calls.

PDF export restores a previously active single-line diagram in a `finally`
block after success or failure. If no current diagram is reported, there is
no diagram to restore. Restoration failure adds a warning to the result message:
a completed export still reports success, while a failed export retains its
original error. Successful single-line restoration was
verified live on SP1 in [FT-26](../evidence/FT-26_pdf_diagram_restoration_sp1.txt).
Failure-path restoration has automated coverage; active plot pages are not covered.
Bootstrap stale-token rejection after creation was verified live in
[FT-25](../evidence/FT-25_bootstrap_confirmation_binding_sp1.txt).

Run the PowerFactory unit and catalog tests from the repository root:

```powershell
python -m pytest PowerFactory/tests -q
```

The installed-wheel smoke test, `tests/check_evemtbench_wheel.py`, runs separately
in CI against an installed package outside the checkout.
Validation records and the contribution and function-test reports are in
[`evidence/`](../evidence/README.md).
