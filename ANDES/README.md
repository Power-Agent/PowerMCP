# ANDES MCP Server

MCP server for ANDES (Python-based power system dynamic analysis), enabling power flow and time-domain simulation.

> **Note:** This MCP server is under active development and may need further modification to handle some internal code output and ensure full compatibility with all ANDES features.

## Requirements

- Python 3.10 or higher
- [ANDES](https://andes.readthedocs.io/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python andes_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "andes": {
      "command": "python",
      "args": ["ANDES/andes_mcp.py"]
    }
  }
}
```

## Available Tools

- **run_power_flow(file_path: str, dyr_path: Optional[str] = None)**: Run power flow analysis on a power system case file.
  - `dyr_path`: optional path to a PSS/E `.dyr` dynamic-model file (generators, exciters, governors) to attach to a PSS/E `.raw` case via ANDES's `addfile` loading. Without it, `run_time_domain_simulation`/`run_eigenvalue_analysis` have no real dynamics to work with beyond static topology.
  - Adds two fields to the returned `power_flow` dict:
    - `n_dynamic_generators`: how many dynamic generator models the loaded system actually carries, summed over ANDES's `SynGen`, `RenGen`, and `DG` groups (synchronous machines and inverter-based resources).
    - `dynamic_models_loaded`: `n_dynamic_generators > 0`. Derived from what attached, not from whether `dyr_path` was passed — ANDES's PSS/E dyr parser skips model types it does not support, so a supplied `.dyr` can still leave the system with no dynamics. A case with dynamics embedded in the file itself (like `kundur_full.json`) reports `True` with no `.dyr` at all.
  - Purely additive: omitting `dyr_path` behaves exactly as before.
- **run_time_domain_simulation(step_size: float = 0.01, t_end: float = 10.0)**: Run time domain simulation on the currently loaded power system.
- **run_eigenvalue_analysis(file_path: str)**: Run eigenvalue (small-signal) analysis on a power system case. Reloads the case fresh from `file_path` and returns:
  - `n_modes`: number of eigenvalues/modes.
  - `modes`: a list, one entry per mode, each with:
    - `index`: the mode's position in ANDES's native eigenvalue ordering.
    - `eigenvalue`: `[real, imag]` parts of the eigenvalue.
    - `frequency_hz`: oscillation frequency in Hz (`0.0` for non-oscillatory/real modes).
    - `damping_ratio_pct`: damping ratio as a percentage. Real modes get `+100`/`-100`, same as ANDES's own report — a real mode at `-100` is monotonic instability.
    - `is_oscillatory`: whether the mode has a non-zero imaginary part.

    The list is sorted **least-damped (most concerning) first**.
  - `participation_factors`: the raw participation-factor matrix from ANDES, in ANDES's native ordering. Use a mode's `index`, not its position in `modes`, to look up its row/column — the `modes` list is re-sorted and this matrix is not.
  - `state_names`: state variable labels, in the same native ordering as `participation_factors`.
  - `success`: whether ANDES's `EIG.run()` reported success.
  - `n_eigenvalues`, `eigenvalues`: the pre-0.3.0 fields, retained so existing callers keep working. The old `eigenvectors` and `state_variables` fields are gone: they read attributes the `EIG` routine has never had, so they only ever returned `[]`.
- **get_system_info()**: Get information about the currently loaded power system.
- **load_network_from_any(...)**: Convert any PowerIO-readable case, or one selected entry of a PowerIO IR collection, into the ANDES run format.
- **load_network_from_json(...)**: Convert serialized PowerIO IR, or one selected entry of it, without staging the source input.

## License note

[ANDES](https://github.com/curent/andes) is GPL-3.0; it is installed only as an optional pip extra (`andes = ["andes"]` in `pyproject.toml`), never vendored into this MIT-licensed repo. The raw+dyr example/test case (`ieee14.raw`/`ieee14.dyr`) is likewise referenced at call time via `andes.get_case(...)` from the installed `andes` package's own bundled `andes/cases/` directory -- never vendored into this repo either.

## Prompt Example

Could you run power flow on the Kundur case at `yourpath\PowerMCP\ANDES\kundur_full.json` using ANDES and summarize the results? Then call `get_system_info` to show the system details.

Or, with a PSS/E raw+dyr case: run power flow on `ieee14.raw` with `dyr_path` set to `ieee14.dyr` (e.g. via `andes.get_case("ieee14/ieee14.raw")` / `andes.get_case("ieee14/ieee14.dyr")` for ANDES's own bundled example), confirm `dynamic_models_loaded` and `n_dynamic_generators` in the result, then run a time-domain simulation against the loaded dynamics.

## Resources

- [ANDES Documentation](https://andes.readthedocs.io/)
