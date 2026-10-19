# DIgSILENT PowerFactory MCP Agent

Connect an AI assistant to DIgSILENT PowerFactory to inspect models, run
calculations and fault simulations, build equipment, and export results.

## Architecture

```text
Claude / AI assistant
        │ MCP protocol
        ▼
MCP_PowerFactory.py                    MCP Python SDK 2 server
        │ Python calls
        ▼
Agent_DIgSILENT.py                     Simulation and shared PowerFactory helpers
        │
        ├── Inherits EvEMTBenchMixin from evemtbench.py
        │       ├── Reads data/evemtbench_*.json
        │       ├── Lists catalogs, filters and creation parameters
        │       └── Plans, creates, verifies and rolls back equipment
        │
        │ Simulation, inspection, export and equipment-creation calls
        ▼
DIgSILENT PowerFactory
        │
        ▼
Outputs: CSV results, PNG plots, diagram PDF, optional .pfd export
```

`evemtbench.py` is part of the agent layer, not a separate MCP server.
Catalog listing returns JSON data without opening PowerFactory. Equipment
creation and simulation require a PowerFactory connection.

## Features

- Model inspection, parameter changes, and study-case management.
- Load flow, short-circuit, contingency analysis, and RMS fault simulations.
- Grid bootstrap, component management, and six EvEMTBench equipment catalogs.
- CSV results, PNG plots, single-line PDF export, and optional project export.

## Implemented Functions

| Task | Main tools | Guide |
|---|---|---|
| Inspect models | `list_components`, `list_objects`, `get_parameters` | [Tool reference](references/tool_guide.md#implemented-functions) |
| Manage study cases and imports | `list_study_cases`, `create_study_case`, `import_project` | [Examples](references/tool_guide.md#prompt-examples) |
| Run calculations | `run_loadflow`, `run_short_circuit` | [Tool reference](references/tool_guide.md#implemented-functions) |
| Simulate faults and read results | `run_custom_case`, `run_simulation`, `read_results_csv` | [Configuration and outputs](references/tool_guide.md#configuration) |
| Run contingency analysis | `list_contingencies`, `run_contingency_analysis`, `get_contingency_summary` | [Contingency tools](references/tool_guide.md#implemented-functions) |
| Bootstrap grids and buses | `create_grid_with_buses` | [Bootstrap](references/tool_guide.md#greenfield-grid-bootstrap) |
| Add or delete equipment | `add_component`, `delete_component` | [Component management](references/tool_guide.md#component-management) |
| Build paper-backed equipment | `list_evemtbench_components`, `create_evemtbench_component` | [EvEMTBench](#evemtbench-equipment) |
| Export a diagram | `export_active_grid_pdf` | [Export behavior](references/tool_guide.md#automated-tests-and-validation-reports) |

The [detailed guide](references/tool_guide.md) contains full tool and agent-method
inventories, parameter examples, and prompt examples.

## EvEMTBench Equipment

Two public MCP tools cover six component families:

- `list_evemtbench_components(component_type, filters)` reads catalog data and
  returns source information, available filters, and creation parameters.
- `create_evemtbench_component(component_type, parameters)` previews or creates
  equipment using the selected catalog.

Supported types: `transformer`, `overhead_line`, `underground_cable`,
`external_grid`, `load`, and `synchronous_machine`.

Discover a line profile without opening PowerFactory:

```python
list_evemtbench_components(
    component_type="overhead_line",
    filters={"voltage_kv": 110, "profile": "p50"},
)
```

Preview a load in an existing grid with a compatible bus:

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
    },
)
```

These are MCP tool-call examples. An empty confirmation creates nothing.
Inspect the preview, then repeat the same request with the exact returned
`confirmation_required` string to apply it. If inputs or resolved project
state change, obtain a fresh preview.

Choose the catalog class or profile explicitly; a paper table alone does not
select equipment. See the [equipment examples](references/tool_guide.md#evemtbench-transformer-database-and-creator),
[source mappings](references/evemtbench.md), and
[component catalog](references/evemtbench_component_catalog.md).

### Scope and safety

- Bootstrap requires an active project and study case. It does not create a
  project or a single-line diagram.
- Lines and cables use sequence equivalents, not geometric ULM models.
  Supply a suitable engineering current rating.
- Transformer zero-sequence and saturation mappings, and load ZIP coefficients,
  remain catalog-only. Synchronous-machine creation supports round rotors only.
- Sampled research inputs need engineering review. Retained-value checks do not
  establish a complete dynamic model or suitability for an energized network.
- Preview/confirmation applies to EvEMTBench creation, bootstrap, and deletion.
  Other tools, including `add_component` and `modify_parameter`, can change
  the model immediately. Inspect returned status and partial-change warnings.

When upgrading from specialized MCP tools, migrate to the two unified tools
and refresh the client's tool list. Internal Python helpers remain available.
See the [detailed guide](references/tool_guide.md) for per-family constraints.

## Configuration

Copy [simulation_config.example.json](simulation_config.example.json) to
`simulation_config.json`. Set the project, study case, output paths, and fault
cases. Do not commit this machine-specific file. Configure
`POWERFACTORY_PYTHON_PATH` or `PYTHONPATH` for the PowerFactory Python module.
See the [configuration guide](references/tool_guide.md#configuration) for details.

## Output Structure

Each run writes CSV results and PNG plots beneath `output_dir/run_label/`,
with an optional `.pfd` project export. See the
[output example](references/tool_guide.md#output-structure).

## Requirements

A licensed Windows installation of PowerFactory with its Python interface is
required for simulations and model changes. Catalog listing works offline.
Use a Python version supported by your PowerFactory installation.
See [INSTALL.txt](INSTALL.txt) and [requirements.txt](requirements.txt) for setup
and dependencies.

## Quick Start

From the `PowerFactory` directory, with your virtual environment active:

```powershell
python -m pip install -r requirements.txt
Copy-Item simulation_config.example.json simulation_config.json
python MCP_PowerFactory.py --transport stdio
```

Before starting the server, configure your project and output paths as described
above. See [INSTALL.txt](INSTALL.txt) for MCP client configuration.

Once connected, start with `ping`, then inspect the context using
`get_active_project` and `get_active_study_case` before requesting changes.

## Prompt Examples

> Inspect the active project and study case, then list ten buses without changes.

> Preview a 20 kV EvEMTBench load on MV Bus in Research Grid using seed 42.
> Return the sampled values and confirmation phrase without creating anything.

See [more prompts](references/tool_guide.md#prompt-examples) for calculations,
fault simulations, component management, and exports.

## EvEMTBench Data Source

Equipment catalogs use [EvEMTBench (Kordowich et al., 2026)](https://arxiv.org/abs/2608.19777).
See [source mappings and limitations](references/evemtbench.md).

## License

MIT

## Automated Tests and Validation Reports

From the repository root:

```powershell
python -m pytest PowerFactory/tests -q
```

The installed-wheel smoke check,
[`check_evemtbench_wheel.py`](tests/check_evemtbench_wheel.py), runs separately
in CI against an installed package outside the checkout. Automated tests do
not replace licensed-runtime validation.

Live records and contribution and function-test reports are indexed in
[`evidence/`](evidence/README.md). See the
[validation notes](references/tool_guide.md#automated-tests-and-validation-reports)
for confirmation binding and PDF diagram restoration limitations.
