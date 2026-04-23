# Surge MCP Server

MCP server for [surge-py](https://pypi.org/project/surge-py/). 44 tools
across 10 categories: case I/O, power flow (AC / DC / FDPF), DC
sensitivities (PTDF / LODF / OTDF), OPF (DC / AC / SCOPF), N-1 and N-2
contingency analysis, NERC and AC Available Transfer Capability, SCED /
SCUC dispatch, inspection, export + graph analytics, and network
construction / editing.

## Requirements

- Python 3.12 – 3.14 (`surge-py` pyo3/maturin range).
- `surge-py >= 0.1.5`.
- `mcp` (official SDK).

### System libraries

Surge loads LP / MIP and NLP solvers at runtime. Install the
open-source pair; commercial solvers are optional.

| Platform | Install |
| --- | --- |
| macOS (Homebrew) | `brew install highs ipopt` |
| Ubuntu / Debian | `sudo apt install libhighs-dev coinor-libipopt-dev` |

`pip install highspy` alone does not satisfy the HiGHS runtime link.
Set `HIGHS_LIB_DIR` and `IPOPT_LIB_DIR` if libraries are in non-standard
locations.

Gurobi, COPT, and CPLEX are runtime plugins. When a license is
available the auto-detect path uses them without further configuration;
otherwise Surge falls back to HiGHS / Ipopt.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python surge_mcp.py
```

MCP client config:

```json
{
  "mcpServers": {
    "surge": {
      "command": "python",
      "args": ["yourpath/PowerMCP/surge/surge_mcp.py"]
    }
  }
}
```

On Windows, use the `cmd /c` form in the root [`config.json`](../config.json).

## Tools

Every tool returns `{"status": "success"|"error", "message": str, "results"?: dict}`.
Network state is held in the server process across calls; no need to
reload between tool invocations.

### Case I/O

- `load_network(file_path, format?)` — load from disk. Extensions:
  `.surge.json.zst`, `.m`, `.raw`, `.rawx`, `.xiidm`, `.uct`, `.dss`,
  `.epc`. `format` overrides detection.
- `save_network(file_path)` — extension-based format.
- `load_builtin_case(name)` — embedded cases: `case9`, `case14`,
  `case30`, `case57`, `case118`, `case300`, `market30`.
- `get_network_info()` — counts, totals, areas, zones, voltage levels.

### Power flow

- `run_ac_power_flow(flat_start, enforce_q_limits, max_iterations, tolerance)` — Newton-Raphson.
- `run_dc_power_flow(headroom_slack)` — lossless linearized.
- `run_fast_decoupled_pf(variant)` — `"xb"` or `"bx"`.

### DC sensitivities

- `compute_ptdf(monitored_branches?, format, top_k_per_branch)`.
- `compute_lodf(outage_branches?, monitored_branches?, format, top_k_per_branch)`.
- `compute_otdf(outage_branches, monitored_branches, format, top_k_per_pair)`.

`format` controls serialization:

- `summary` (default): shape, sparsity, top-*k* largest-|value| entries.
- `sparse`: CSR for 2-D, coordinate list for OTDF.
- `full`: dense nested list. Refused for `LodfMatrixResult` above 500
  branches and for OTDF 3-D tensors.

### OPF

- `run_dc_opf(lp_solver)` — `default` / `highs` / `gurobi` / `copt` / `cplex`.
- `run_ac_opf(nlp_solver)` — `default` / `ipopt` / `copt` / `gurobi`.
- `run_scopf(lp_solver, nlp_solver)` — N-1-screened SCOPF.

### Contingency

- `run_n1_branch_contingency(monitored_branches?)`.
- `run_n1_generator_contingency()`.
- `run_n2_branch_contingency()`.

Each returns the full `ContingencyAnalysis.to_dict()` payload: summary
counts, per-contingency `results`, and a flat `violations` list
(thermal, voltage, non-convergent, islanding, flowgate, interface).

### Transfer capability

- `compute_nerc_atc(source_buses, sink_buses, name?, trm_fraction, cbm_mw, etc_mw)` — NERC MOD-029 / MOD-030.
- `compute_ac_atc(source_buses, sink_buses, name?, v_min, v_max)` — AC-aware with reactive margin.

### Dispatch

- `run_sced(request?, lp_solver)` — single-period. `request=None`
  defaults to DC SCED with all generators committed.
- `run_scuc(request?, lp_solver)` — multi-period unit commitment.

### Inspection

- `list_buses(limit?, sort_by?, ascending?)` — bus rows with metadata.
- `list_branches(limit?, sort_by?, ascending?)` — branch rows with metadata.

### Export & graph analytics

- `export_tables(output_dir)` — buses / branches / generators / loads / shunts CSVs.
- `get_topology(as_networkx?, in_service_only?)` — nodes + edges, optional adjacency dict.
- `find_path(from_bus, to_bus, in_service_only?)` — BFS shortest path.
- `get_islands()` — connected components.
- `get_dispatch_request_schema()` — JSON schema for the `run_sced` /
  `run_scuc` `request` argument.

### Network construction & editing

- `create_empty_network(name?, base_mva?, freq_hz?)`.
- `add_bus(number, bus_type, base_kv, ...)`,
  `add_generator(bus, p_mw, pmax_mw, ...)`,
  `add_load(bus, pd_mw, qd_mvar, ...)`,
  `add_line(from_bus, to_bus, r_ohm_per_km, x_ohm_per_km, ...)`,
  `add_transformer(from_bus, to_bus, mva_rating, v1_kv, v2_kv, z_percent, ...)`,
  `add_storage(bus, charge_mw_max, discharge_mw_max, energy_capacity_mwh, ...)`.
- `set_branch_rating`, `set_branch_in_service`,
  `set_generator_limits`, `set_generator_in_service`.
- `scale_loads(factor, area?)`, `scale_generators(factor, area?)`.
- `remove_bus`, `remove_branch`, `remove_generator`, `remove_load`.

## Troubleshooting

- `ImportError: symbol not found: libipopt` — set `IPOPT_LIB_DIR` to
  the directory containing `libipopt.{so,dylib}`. macOS/Homebrew:
  `export IPOPT_LIB_DIR=/opt/homebrew/lib`.
- `HiGHS solver unavailable` — install HiGHS system-wide (see
  [System libraries](#system-libraries)); `pip install highspy` is not
  sufficient.
- `no network loaded` — call `load_network`, `load_builtin_case`, or
  `create_empty_network` before any analysis tool.
- AC PF does not converge — try `flat_start=True` or increase
  `max_iterations`. Inspect `max_mismatch` in the result.
- Sensitivity tools return summary only — pass `format="sparse"` or
  `format="full"` for CSR / dense matrices.

## Resources

- [surge-py on PyPI](https://pypi.org/project/surge-py/)
- [Amptimal Surge](https://github.com/amptimal/surge)
