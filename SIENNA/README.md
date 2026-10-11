# SIENNA MCP Connector

This connector exposes four tools for the open-source Sienna / PowerSystems.jl /
PowerSimulations.jl stack:

- `load_system`: inspect an R2X System JSON and report component counts.
- `translate_to_plexos`: translate an R2X System JSON to PLEXOS-shaped components.
- `run_sienna_solve`: execute a PowerSimulations.jl economic-dispatch solve through Julia and HiGHS.
- `compare_solutions`: compare component counts or numeric fields in two result JSON files.

## Installation

From the repository root, install the supported optional dependencies with:

```bash
python -m pip install -e ".[sienna]"
```

The SIENNA optional dependency group is supported on Python 3.11–3.13. It pins
`r2x-plexos>=0.3.0` rather than the `r2x==2.1.0` meta-package dependency
that resolves to the affected `r2x-plexos==0.2.0` line (R2X#299).

For a standalone install from this directory, use Python 3.11–3.13:

```bash
python -m pip install .
```

## Julia setup

`run_sienna_solve` requires a local Julia installation and these packages in its
Julia environment:

```julia
using Pkg
Pkg.add(["PowerSystems", "PowerSimulations", "HiGHS", "JSON3"])
Pkg.precompile()
```

Configure `julia_bin` through the PowerMCP installer/configuration, or set
`SIENNA_JULIA_BIN`. If packages are installed in a non-default Julia depot,
configure `julia_depot_path` or `JULIA_DEPOT_PATH`.

The Julia subprocess has been manually verified against Julia 1.10.9,
PowerSystems.jl 5.12.1, PowerSimulations.jl 0.38.2, and HiGHS.jl 1.24.1.
The automated tests mock the Julia subprocess and do not provision this toolchain.

## Important JSON-format limitation

The Python-side `r2x_core.System` JSON schema and native Julia
`PowerSystems.jl` JSON schema do **not** round-trip through one another in the
verified versions (R2X 2.1.0 and PowerSystems.jl 5.12.1):

- R2X System JSON is produced/consumed by `r2x_core.System`, and is the format
  used by `load_system` and `translate_to_plexos`.
- Native PowerSystems.jl JSON is produced by Julia's `PowerSystems.to_json`
  and is the format consumed by `run_sienna_solve`.

A Python/R2X JSON file therefore cannot currently be passed directly to
`run_sienna_solve`; a native Julia re-export/format bridge is required.
Conversely, native Julia JSON is not directly loadable through
`r2x_core.System.from_json`. This is a known interoperability gap, not an
implicit conversion. A future adapter/bridge should be validated separately.

Full PLEXOS XML/database export through `translate_to_plexos(export_xml=True)`
is best-effort and needs PLEXOS-specific configuration, including
`horizon_year`. Errors are returned in the `xml_export` field.

## Tests

Run the connector's mocked unit tests with:

```bash
python -m pytest SIENNA/tests -q
```

The tests do not require a PLEXOS license or a local Julia installation.
