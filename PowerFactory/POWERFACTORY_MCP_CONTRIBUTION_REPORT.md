# PowerMCP PowerFactory Tooling Contribution Report

**Status:** Local contribution, not pushed to Repo
**Final verified branch:** `feat/powerfactory-switchgear`
**Latest verified commit:** `8521cb6` (`Insert PowerFactory components using diagram layout tool`)
**Verification completed:** 1 September 2026
**Target system:** DIgSILENT PowerFactory 2026 SP1 with Python 3.10

## 1. Executive summary

This work extends the PowerFactory integration in PowerMCP with a coherent set of read-only discovery tools and guarded model-editing tools. The contribution enables an AI client to inspect the active PowerFactory context, discover objects, read selected parameters, create supported network components with optional single-line diagram synchronization and circuit breakers, and safely preview or perform exact-name deletion.

Eight MCP tools were created:

1. `get_active_project`
2. `get_active_study_case`
3. `get_parameters`
4. `list_objects`
5. `list_components`
6. `list_study_cases`
7. `add_component`
8. `delete_component`

The implementation was verified with 12 automated tests and live calls from the VS Code AI chat client against a running PowerFactory project. Live verification included in-service component creation, graphical insertion and deletion, automatic circuit-breaker creation, parameter inspection, load-flow calculations, short-circuit calculations, guarded deletion, hierarchical cleanup, absence checks, and post-cleanup calculations.

The work remains local. It has not been pushed to the online PowerMCP repository.

## 2. Baseline and scope

The comparison baseline was the online `main` branch of `Power-Agent/PowerMCP`, specifically:

- [PowerFactory/MCP_PowerFactory.py](https://github.com/Power-Agent/PowerMCP/blob/main/PowerFactory/MCP_PowerFactory.py)
- [PowerFactory/Agent_DIgSILENT.py](https://github.com/Power-Agent/PowerMCP/blob/main/PowerFactory/Agent_DIgSILENT.py)

The online baseline already provided connectivity, configuration, project import, study-case creation, parameter modification, load flow, short-circuit calculation, RMS simulation, custom-case execution, and result-file reading. It did not provide the final eight inspection, discovery, creation, and deletion tools listed above.

The supported component scope was intentionally limited to classes available in the test grid:

| Friendly type | PowerFactory class |
|---|---|
| Bus | `ElmTerm` |
| Load | `ElmLod` |
| Generator | `ElmSym` |
| Line | `ElmLne` |
| Two-winding transformer | `ElmTr2` |

Support for shunts, batteries, static generators, three-winding transformers, and other classes was not added without a representative test object and a verified PowerFactory data model.

## 3. Contributed MCP tools

### 3.1 `get_active_project`

Returns the active PowerFactory project's name and full object path.

Key behavior:

- Uses the MCP process's existing PowerFactory application handle.
- Returns a clear failure when PowerFactory is not connected.
- Returns a clear failure when no project is active.
- Does not activate or modify a project.

Typical result:

```json
{
  "success": true,
  "name": "test",
  "full_name": "\\ic84yhos.IntUser\\test.IntPrj"
}
```

### 3.2 `get_active_study_case`

Returns the active study case's name and full object path.

This tool is useful before mutations or calculations because it allows the AI client to confirm the current study context without changing it.

### 3.3 `get_parameters`

Reads multiple PowerFactory attributes from objects selected with a PowerFactory object query.

Signature:

```text
get_parameters(object_query, variables, max_results=100)
```

Key behavior:

- Requires at least one non-empty variable.
- Removes duplicate variable names while preserving order.
- Uses `GetCalcRelevantObjects` for object selection.
- Limits results to between 1 and 1,000 objects.
- Returns total and returned object counts.
- Captures unsupported-attribute errors per object rather than failing the entire request.
- Converts non-JSON-native PowerFactory values to strings.

Example:

```text
object_query="Bus 01.ElmTerm"
variables=["uknom", "outserv"]
max_results=5
```

### 3.4 `list_objects`

Lists calculation-relevant objects using a raw PowerFactory query.

Example:

```text
list_objects(object_query="*.ElmTerm", max_results=3)
```

The response includes object name, class, full path, total count, and returned count. This is the expert-level discovery interface for callers that already know PowerFactory class names.

### 3.5 `list_components`

Lists objects using friendly equipment categories instead of raw class queries.

Supported categories include:

- `all`
- `buses`
- `lines`
- `branches`
- `transformers`
- `loads`
- `generators`
- `synchronous_generators`
- `static_generators`
- `pv_systems`
- `storage`
- `external_grids`
- `switches`

One category can map to multiple PowerFactory classes. Results are deduplicated by full object path and include the out-of-service state when available.

### 3.6 `list_study_cases`

Lists study cases in the active project's study-case folder and marks the active case with `is_active=true`.

The tool returns a controlled result count and fails clearly if PowerFactory is disconnected or the study-case folder cannot be found.

### 3.7 `add_component`

Provides one public creation interface for all five supported component types.

Signature:

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

Required parameters by type:

| Type | Required `parameters` entries | Optional entries |
|---|---|---|
| Bus | `nominal_voltage_kv` | — |
| Load | `bus_name`, `active_power_mw` | `reactive_power_mvar` |
| Generator | `bus_name`, `template_generator`, `active_power_mw` | `reactive_power_mvar` |
| Line | `bus1_name`, `bus2_name`, `template_line`, `length_km` | — |
| Transformer | `high_voltage_bus_name`, `low_voltage_bus_name`, `template_transformer` | — |

Safety and validation include:

- Supported-type allowlist.
- Required-parameter validation.
- Finite and range-checked numeric inputs.
- Distinct terminal buses for lines and transformers.
- Explicit grid selection when multiple grids are active.
- Exact duplicate-name protection within the selected grid.
- Exact bus and template lookup.
- Template-type reuse for typed equipment.
- Cubicle creation and terminal connection.
- Post-write attribute verification.
- Rollback of the new element and its cubicles when setup or verification fails.

### 3.8 `delete_component`

Provides guarded deletion for the same five component types.

Signature:

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

Safety behavior:

- Uses a supported-type allowlist.
- Selects one grid explicitly when necessary.
- Uses exact component-name matching.
- Defaults to preview-only behavior.
- Returns the exact confirmation phrase required for deletion.
- Requires confirmation in the form `DELETE <type> <exact name>`.
- Prevents deletion of a bus that still has connected cubicles.
- Removes associated cubicles for connected equipment.
- Verifies that the component and its created connections are absent afterward.

Deletion is deliberately more guarded than creation because it permanently removes project data and may affect references, calculations, events, scripts, and diagrams.

## 4. Internal architecture added

The public tools reuse a small group of internal helpers:

| Helper | Responsibility |
|---|---|
| `_select_grid` | Resolve one active grid or require an explicit grid name |
| `_select_bus` | Resolve an exact bus within the selected grid |
| `_get_application` | Reuse the shared PowerFactory application handle |
| `_get_template_type` | Find and validate the type of template equipment |
| `_set_and_verify_attributes` | Write and confirm retained PowerFactory attributes |
| `_rollback_connected_element` | Remove a failed element and its cubicles |
| `_create_connected_element` | Create elements, cubicles, terminal assignments, and verified attributes |
| `_agent_result` | Keep MCP wrappers thin and route calls through the dedicated PowerFactory thread |

All PowerFactory calls continue to use the existing single-thread executor because the PowerFactory API requires consistent thread affinity.

## 5. Development and simplification history

The functionality was developed incrementally and then consolidated.

### State inspection and discovery

- `c117064` — Add PowerFactory state inspection MCP tools
- `63e0d8f` — Add PowerFactory component discovery MCP tool

### Component creation and safety

Initial specialized creation functions were implemented and tested for buses, loads, generators, lines, and transformers. Shared application, connection, template, verification, and rollback logic was then consolidated.

Important commits include:

- `ad29fde` — Add safe PowerFactory bus creation MCP tool
- `160a67b` — Add safe PowerFactory load creation MCP tool
- `194f50d` — Add safe PowerFactory generator creation MCP tool
- `63b77c9` — Add safe PowerFactory line creation MCP tool
- `d398b30` — Add safe PowerFactory transformer creation MCP tool
- `8e5f8aa` — Consolidate PowerFactory component connection helpers
- `dd6e464` — Share PowerFactory component template lookup
- `ff1323a` — Share PowerFactory component attribute verification
- `a508f40` — Centralize PowerFactory component verification and rollback

### Generic creation and deletion

- `9a94a13` — Add guarded PowerFactory component deletion MCP tool
- `d57fe29` — Add generic PowerFactory component creation MCP tool
- `003fa6e` — Consolidate PowerFactory component creation

The five specialized public creation functions were removed after their behavior was incorporated directly into `add_component`.

### Final integration

- `eb3da8b` — Consolidate PowerFactory MCP tools

This merge combines the state-inspection branch and the component-management branch into `feat/powerfactory-tools`. Both source branches were retained as local backups.

### Graphical synchronization and switchgear

- `d8510c7` — Synchronize PowerFactory component diagram updates
- `0db824b` — Add circuit breakers to PowerFactory component connections
- `8521cb6` — Insert PowerFactory components using diagram layout tool

These commits extend `add_component` and `delete_component`; they do not expose separate graphical or switchgear MCP tools. Graphical synchronization is requested with `update_graphics=true`. Every generated connection cubicle receives one closed `StaSwitch` circuit breaker.

## 6. Automated verification

The final verified branch passed compilation and 12 unit tests:

```text
Ran 12 tests in 0.006s
OK
```

Tests cover:

1. Bus creation, validation, duplicate protection, grid selection, and rollback.
2. Load creation, bus lookup, numeric validation, duplicate protection, and rollback.
3. Generator creation, template lookup, duplicate protection, and rollback.
4. Line creation, distinct buses, template lookup, duplicate protection, and rollback.
5. Transformer creation, distinct buses, template lookup, duplicate protection, and rollback.
6. Generic component-type and parameter validation.
7. Guarded deletion, confirmation validation, bus-connection protection, cubicle cleanup, and absence verification.
8. Requested graphical insertion, graphical-object deletion, and application rebuild.
9. Closed circuit-breaker creation in each generated connection cubicle.
10. Friendly component discovery.
11. Active project, active study case, multi-parameter reading, raw object discovery, and study-case discovery.
12. K-neighbourhood diagram-layout selection, execution, restoration, and rebuild.

The `[ERROR]` messages printed during unit testing are expected negative-path logs. The tests deliberately trigger invalid inputs and simulated PowerFactory failures, then verify that the operation returns failure and rolls back safely. The unittest outcome remained `OK`.

## 7. Live PowerFactory verification

### 7.1 Discovery and inspection

All consolidated read-only tools were called successfully through the VS Code AI chat client.

Verified observations included:

- Active project: `test`
- Active study case: `Case 1`
- `Bus 01.ElmTerm`: `uknom=345.0`, `outserv=0`
- Bus discovery: 39 total `ElmTerm` objects
- Study-case discovery: 7 study cases, with `Case 1` correctly marked active
- Raw object discovery and friendly bus discovery returned consistent object identities

### 7.2 Bus, line, and load creation

The AI client created an in-service temporary bus, line, and load using `add_component`. The line connected `Bus 01` to the new bus, and the load connected to the new bus. Load flow returned:

```json
{"success": true, "message": "Load flow OK"}
```

Duplicate-name checks were also exercised successfully. The temporary objects were subsequently deleted in dependency-safe order.

### 7.3 Generator and transformer creation

An in-service generator was created as:

```text
MCP Verification Generator 20260822A.ElmSym
```

Verified retained state:

- `pgini=1.0`
- `qgini=0.0`
- `outserv=0`
- Connected to the new cubicle at `Bus 01`
- Reused `Type Gen 01.TypSym`

An in-service transformer was created as:

```text
MCP Verification Transformer 20260822A.ElmTr2
```

Verified retained state:

- `outserv=0`
- High-voltage cubicle connected at `Bus 02`
- Low-voltage cubicle connected at `Bus 30`
- Reused `Trf Type 02 - 30 YNy0.TypTr2`

### 7.4 Electrical calculations

The following calculations succeeded:

1. Load flow with the temporary generator in service.
2. Short-circuit calculation with the temporary generator in service.
3. Load flow with the temporary generator and transformer in service.
4. Short-circuit calculation with the temporary generator and transformer in service.
5. Load flow after deleting both temporary components.
6. Short-circuit calculation after deleting both temporary components.

Successful messages were:

```json
{"success": true, "message": "Load flow OK"}
```

```json
{"success": true, "message": "Short-circuit calculation OK"}
```

### 7.5 Deletion and cleanup

Guarded deletion was exercised live for buses, loads, generators, lines, and transformers. Preview-only responses returned the exact required confirmation phrase. Incorrect confirmation was rejected. Confirmed deletion removed the target object and associated cubicles.

Final exact-name absence checks for the in-service generator and transformer returned:

```json
{
  "success": true,
  "total_count": 0,
  "returned_count": 0,
  "results": []
}
```

The PowerFactory model remained calculation-ready after cleanup.

### 7.6 Graphical synchronization and circuit breakers

With `update_graphics=true`, a temporary out-of-service load was inserted into the active single-line diagram. Confirmed deletion removed its `IntGrf` object and rebuilt the application view, after which live visual inspection confirmed that the symbol disappeared.

A second temporary load verified generated switchgear. Its Bus 01 connection referenced a generated `StaCubic`, whose child `StaSwitch` retained:

```text
aUsage = cbk
on_off = 1
```

The load retained `outserv=1`, showing that component service state and breaker state are independent. After confirmed deletion, the exact load query returned no object, the project-wide switch count returned from 122 to its baseline of 121, and load flow still succeeded.

Expanded verification created an in-service bus, line, load, generator, and
transformer. The switch count rose from the 121 baseline to 127, with exactly
six matching closed circuit breakers: two for the line, one for the load, one
for the generator, and two for the transformer. All five objects were then
deleted with graphical updates enabled. Each exact object query returned zero,
the switch count returned to 121, and both load flow and short-circuit
calculation succeeded after cleanup.

The graphical test also identified an automatic-layout limitation: direct
insertion of an isolated bus can position it far from the existing network.
Creating the bus without graphics and inserting it together with its first
connecting line produced a correctly anchored graphical result.

## 8. Credibility assessment

### Read-only tools

The six discovery and inspection tools are credible low-risk interfaces for controlled PowerMCP use. They expose state without modifying it, bound result sizes, and return explicit disconnected or missing-object failures.

### `add_component`

`add_component` is credible for controlled local use because all supported component types were created live, connections, circuit breakers, retained attributes, and requested graphical insertion were verified, calculations succeeded with components in service, and rollback paths were unit-tested.

### `delete_component`

`delete_component` is credible for controlled local use with stronger operational caution. Its preview, exact confirmation, bus protection, graphical cleanup, cubicle and switchgear cleanup, and absence verification materially reduce risk, but confirmed deletion remains inherently destructive.

## 9. Known limitations and boundaries

1. **Opt-in diagram synchronization:** Diagram insertion and deletion require `update_graphics=true`; the default is `false`.
2. **No multi-call transaction:** A sequence of separate MCP calls is not atomic. Earlier successful calls remain if a later call fails.
3. **Template dependency:** Generator, line, and transformer creation requires valid existing template equipment and types.
4. **Runtime generic schema:** Type-specific `parameters` are validated at runtime because `add_component` uses one generic dictionary.
5. **Destructive deletion:** Confirmed deletion has no MCP-level undo.
6. **Project-wide effects:** Network-model changes may affect more than the active study case. A study-case switch does not necessarily restore deleted network data.
7. **Supported-class boundary:** Creation and deletion are limited to `ElmTerm`, `ElmLod`, `ElmSym`, `ElmLne`, and `ElmTr2`.
8. **PowerFactory attribute knowledge:** `get_parameters` requires valid PowerFactory attribute names. Measurement attributes may require a completed calculation.
9. **Complex reference formatting:** PowerFactory object references are returned as string representations when they are not JSON-native values.
10. **Protection-device boundary:** Generated cubicles currently receive a circuit breaker only. Relay, CT, and VT creation is outside the implemented scope.
11. **Isolated-bus placement:** Direct graphical insertion of an unconnected bus can place it far from the existing network and expand the fitted viewport. Inserting it with its first connecting line provides a better anchor.

## 10. Example workflow

### Discover context

```text
ping
create_study_case(case_name="Case 1", base_study_case="0. Base")
get_active_project()
get_active_study_case()
list_components(component_type="buses", max_results=10)
```

### Create and inspect a bus

```json
{
  "component_type": "bus",
  "component_name": "Example MCP Bus",
  "parameters": {
    "nominal_voltage_kv": 110.0
  },
  "grid_name": "Grid",
  "out_of_service": true,
  "open_digsilent": true,
  "update_graphics": true
}
```

```text
get_parameters(
    object_query="Example MCP Bus.ElmTerm",
    variables=["uknom", "outserv"],
    max_results=5
)
```

### Preview and confirm deletion

Preview:

```text
delete_component(
    component_type="bus",
    component_name="Example MCP Bus",
    grid_name="Grid"
)
```

Confirmed deletion:

```text
delete_component(
    component_type="bus",
    component_name="Example MCP Bus",
    grid_name="Grid",
    confirmation="DELETE bus Example MCP Bus",
    update_graphics=true
)
```

## 11. Files affected

The final contribution modifies or adds:

- `PowerFactory/Agent_DIgSILENT.py`
- `PowerFactory/MCP_PowerFactory.py`
- `PowerFactory/test_component_creation.py`
- `PowerFactory/test_state_inspection.py`

This report is intended to be added as:

- `PowerFactory/POWERFACTORY_MCP_CONTRIBUTION_REPORT.md`

## 12. Recommended next actions

The implementation and verification are complete. If the contribution is prepared for upstream review, the remaining non-code work is:

1. Review this report.
2. Add concise user documentation for the eight tools to the repository README or PowerFactory documentation.
3. Rebase the local integration branch on the latest online `main` branch.
4. Re-run the 12 tests and one live smoke test after rebasing.
5. Push only when the contribution is intentionally ready for review.

## 13. Conclusion

AI clients can now establish their active context, discover available objects, inspect selected attributes, safely create supported network equipment, execute calculations against the modified model, and remove temporary equipment through a guarded workflow.
