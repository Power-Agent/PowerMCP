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

### Configuration

| Tool | Purpose |
|------|---------|
| **compile_opendss_file** | `ClearAll` + compile a master DSS file; `payload` includes `circuit_readiness`, `circuit_loaded`; may skip recompile when the same file is already loaded (unless `force_recompile`). |
| **clear_all_opendss_memory** | `ClearAll`; resets `circuit_loaded` and `solution_available`. |

### Model

| Tool | Purpose |
|------|---------|
| **get_model_summary_records** | `model._summary_model_records` |
| **get_buses_records** | `model._buses_records` |
| **get_lines_records** | `model._lines_records` (`payload` null if no lines) |
| **get_transformers_records** | `model._transformers_records` |
| **get_meters_records** | `model._meters_records` |
| **get_monitors_records** | `model._monitors_records` |
| **get_generators_records** | `model._generators_records` |
| **get_vsources_records** | `model._vsources_records` |
| **get_regcontrols_records** | `model._regcontrols_records` |
| **get_loads_records** | `model._loads_records` |
| **get_pvsystems_records** | `model._pvsystems_records` |
| **get_storage_records** | `model._storage_records` |
| **get_segments_records** | `model._segments_records` |
| **get_enabled_segments_records** | `model._enabled_segments_records` |
| **get_disabled_segments_records** | `model._disabled_segments_records` |
| **get_pc_elements_records** | `model._pc_elements_records` |
| **get_enabled_pc_elements_records** | `model._enabled_pc_elements_records` |
| **get_disabled_pc_elements_records** | `model._disabled_pc_elements_records` |
| **get_pd_elements_records** | `model._pd_elements_records` |
| **get_enabled_pd_elements_records** | `model._enabled_pd_elements_records` |
| **get_disabled_pd_elements_records** | `model._disabled_pd_elements_records` |
| **get_element_data** | Property dict for a named element (`element_class`, `element_name`). |
| **is_element_in_model** | Whether an element exists (`element_class`, `element_name`). |
| **edit_element** | Set properties on an existing element; clears `solution_available` (re-solve after). |
| **add_element** | Add an element from DSS definition text; clears `solution_available` (re-solve after). |
| **disable_elements_by_type** | Disable elements by OpenDSS type; clears `solution_available` (re-solve after). |
| **add_line_in_vsource** | `model.add_line_in_vsource` — feeder-head line; optional meter/monitors; clears `solution_available` (re-solve after). |

### Simulation

| Tool | Purpose |
|------|---------|
| **solve_snapshot** | Snapshot power-flow solve (requires compiled circuit); optional `control_mode`, `max_iterations`, `max_control_iter`; sets `solution_available`; `payload` includes solve status. |

### Results (after **solve_snapshot**)

| Tool | Purpose |
|------|---------|
| **get_results_summary_records** | `results._summary_records` |
| **get_voltage_mag_ln_nodes_records** | `results._voltage_mag_ln_nodes_records` |
| **get_voltage_ang_ln_nodes_records** | `results._voltage_ang_ln_nodes_records` |
| **get_voltage_mag_ll_nodes_records** | `results._voltage_mag_ll_nodes_records` |
| **get_voltage_ang_ll_nodes_records** | `results._voltage_ang_ll_nodes_records` |
| **get_voltage_mag_smart_nodes_records** | `results._voltage_mag_smart_nodes_records` |
| **get_voltage_ang_smart_nodes_records** | `results._voltage_ang_smart_nodes_records` |
| **get_powers_p_records** | `results._powers_p_records` |
| **get_powers_q_records** | `results._powers_q_records` |
| **get_losses_p_records** | `results._losses_p_records` |
| **get_losses_q_records** | `results._losses_q_records` |
| **get_currents_element_mag_records** | `results._currents_element_mag_records` |
| **get_currents_element_ang_records** | `results._currents_element_ang_records` |
| **get_currents_element_norm_amps_records** | `results._currents_element_norm_amps_records` |
| **get_currents_element_emerg_amps_records** | `results._currents_element_emerg_amps_records` |
| **get_voltages_element_mag_records** | `results._voltages_element_mag_records` |
| **get_voltages_element_ang_records** | `results._voltages_element_ang_records` |
| **get_all_losses_records** | `results._all_losses_records` |
| **get_violation_voltage_ln_nodes_records** | LN nodal voltage violations; optional `v_min_pu` / `v_max_pu` (defaults 0.95 / 1.04); structured `payload` with `records` and limit metadata. |
| **get_violation_voltage_ll_nodes_records** | LL nodal voltage violations; same limit parameters and payload shape as LN. |
| **get_violation_voltage_nodes_records** | Smart LN/LL nodal voltage violations; same limit parameters and payload shape. |
| **get_current_loading_percent_records** | Thermal loading percent; optional `current_limit_type` (`norm_amps` or `emerg_amps`); structured `payload` with `records` and limit metadata. |
| **get_violation_currents_elements_records** | Elements over current loading threshold; same `current_limit_type` and payload shape as loading percent. |

### Interactive view

| Tool | Purpose |
|------|---------|
| **get_voltage_profile_plotly_figure** | Voltage vs distance from `interactive_view.voltage_profile` as Plotly JSON (`payload.plotly_json`); typically needs an energymeter; use **add_line_in_vsource** then **solve_snapshot** if missing. |
| **get_opendss_circuit_map_plotly_figure** | Feeder map from `interactive_view.circuit_plot` as Plotly JSON (`payload.plotly_json`); needs bus coordinates (e.g. `BusCoords`). Optional `parameter` (e.g. `active power`, `voltage`). |

## Example

What are the voltages at all buses in the IEEE 13-bus feeder?
The DSS file is located at <path_to_your_dss_file>

## Resources

- [OpenDSS](https://opendss.epri.com/IntroductiontoOpenDSS.html)
- [py-dss-interface](https://github.com/PauloRadatz/py_dss_interface)
- [py-dss-toolkit](https://github.com/PauloRadatz/py_dss_toolkit)
