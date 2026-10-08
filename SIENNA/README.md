# SIENNA MCP Server

MCP connector for [Sienna](https://github.com/Sienna-Platform) (`PowerSystems.jl` /
`PowerSimulations.jl`), the open-source Julia power-systems modeling toolchain. Exposes four
tools:

- `load_system` -- load a Sienna PSY-JSON system and summarize its components.
- `translate_to_plexos` -- translate a Sienna system to PLEXOS-shaped components via
  [`r2x`](https://pypi.org/project/r2x/).
- `run_sienna_solve` -- run a `PowerSimulations.jl` economic-dispatch solve (open-source HiGHS
  solver) against a Sienna system, via a local Julia install.
- `compare_solutions` -- diff a Sienna-side artifact against a PLEXOS-side artifact.

No PLEXOS license, Sienna license, or vendor network call is required anywhere in this
connector. `translate_to_plexos` and `compare_solutions` call `r2x` directly -- there is no
PowerMCP-authored bridge/interop module, the same relationship `pandapower`/`PyPSA`/`Egret`/
`ANDES` have with `powerio` in this repo.

This is the counterpart to the sibling `PLEXOSDB` connector (PLEXOS CRUD +
`translate_to_sienna`, [issue #53](https://github.com/Power-Agent/PowerMCP/issues/53)) -- out
of scope here, mentioned only because it's a compatible producer/consumer for some of this
connector's tools (see "Known gaps" below for exactly how compatible).

## Install

```bash
pip install powermcp[sienna]
```

This installs `r2x` (which pulls in `r2x-core`, `r2x-plexos`, `r2x-sienna`,
`r2x-sienna-to-plexos` as its own transitive dependencies -- verified against `r2x==2.1.0`).
`r2x` is enough for `load_system`, `translate_to_plexos`, and the System-JSON side of
`compare_solutions`. `run_sienna_solve` additionally needs a local Julia install with
`PowerSystems.jl`, `PowerSimulations.jl`, `HiGHS.jl`, and `JSON3.jl` -- see below.

## Julia setup (for `run_sienna_solve`)

1. Install Julia 1.10+ (verified against 1.10.9): https://julialang.org/downloads/

2. Install the required Julia packages into your default environment (or a dedicated one --
   point `julia_depot_path` at it, see below):

   ```bash
   julia -e 'using Pkg; Pkg.add(["PowerSystems", "PowerSimulations", "HiGHS", "JSON3"]); Pkg.precompile()'
   ```

   Verified package versions this connector's Julia driver script
   (`sienna_mcp/scripts/solve_system.jl`) was developed and tested against:
   `PowerSystems.jl 5.12.1`, `PowerSimulations.jl 0.38.2`, `HiGHS.jl 1.24.1`.

3. Run the PowerMCP install wizard (or set the equivalent env vars) to capture:

   - `julia_bin` -- path to the `julia` executable (or set `SIENNA_JULIA_BIN`).
   - `julia_depot_path` -- optional; sets `JULIA_DEPOT_PATH` for the subprocess if your Julia
     packages live in a non-default depot (or set `JULIA_DEPOT_PATH` directly).

   This mirrors the `HOPE` connector's own `julia_bin`/`julia_depot_path` config keys
   (`powermcp/registry.py`) -- `run_sienna_solve` shells out to `julia` as a subprocess, the
   same mechanism `HOPE` uses (not `juliacall`/`PyJulia`). Unlike `HOPE`, there is no
   `repo_root` config key: Sienna is a set of registered Julia packages, not a local git
   checkout.

## Loading a Sienna PSY JSON

`load_system` accepts a PSY-JSON file and uses `r2x_core.System.from_json` (part of the `r2x`
PyPI distribution) to deserialize it, returning a component-type-count summary rather than the
full system (systems can be large). Two producers of compatible input:

- The sibling `PLEXOSDB` connector's `translate_to_sienna` tool
  ([issue #53](https://github.com/Power-Agent/PowerMCP/issues/53), out of scope here) --
  produces `r2x_core.System` JSON directly, since it also goes through `r2x` on the Python
  side. This is the input `load_system`/`translate_to_plexos` are built for.
- Anything else that writes `r2x_core.System.to_json`-compatible JSON.

**Important: this is not the same JSON format PowerSystems.jl's own native `to_json`/`System()`
constructor read and write on the Julia side.** See "Known gaps" below -- this was verified,
not assumed.

## Known gaps (verified during development, not assumed)

**The Python `r2x_core.System` JSON schema and the native Julia `PowerSystems.jl` JSON schema
do not round-trip through each other, in either direction**, as of `r2x 2.1.0` /
`PowerSystems.jl 5.12.1`:

- A system built and serialized in Python via `r2x_core.System`/`r2x_sienna.models` (top-level
  keys: `name`, `description`, `uuid`, `data_format_version`, `components`,
  `supplemental_attributes`, `time_series`, `system_base_power`, `r2x_core_version`) fails to
  load via Julia's `PowerSystems.System(path)` constructor
  (`MethodError: no method matching VersionNumber(::Nothing)`, because
  `data_format_version` is `None`/absent in the Python-written file).
- A system built and serialized natively in Julia via `PowerSystems.to_json` (top-level keys:
  `data`, `data_format_version`, `frequency`, `internal`, `metadata`, `runchecks`,
  `units_settings` -- a structurally different schema) fails to load via Python's
  `r2x_core.System.from_json` (`KeyError: 'time_series'`).

Practical consequence: **`load_system`/`translate_to_plexos` (Python, via `r2x_core`) and
`run_sienna_solve` (Julia, via `PowerSystems.System(path)`) currently expect two different "PSY
JSON" dialects.** A file produced by `translate_to_sienna` (#53, Python/`r2x_core`-shaped) can
be `load_system`'d and `translate_to_plexos`'d by this connector, but **cannot** be fed
directly into `run_sienna_solve` without a native-Julia re-export step first (e.g., load it
into a Julia session some other way and call `PowerSystems.to_json` on it). Conversely, a
system exported natively from a real Sienna/PowerSystems.jl model (via `to_json` on the Julia
side) is exactly what `run_sienna_solve` expects, but is **not** directly loadable by
`load_system`/`translate_to_plexos` on the Python side.

Closing this gap (a real format bridge between the two schemas) is out of scope for this issue
and not attempted here; it is called out explicitly rather than silently papered over. Until
then, treat `load_system`/`translate_to_plexos` as the Python/`r2x`-ecosystem half of this
connector and `run_sienna_solve` as the native-Julia half, each expecting its own native input.

`translate_to_plexos`'s `export_xml=True` full-PLEXOS-database export
(`r2x_plexos.PLEXOSExporter`) is similarly best-effort: it requires more PLEXOS-specific
configuration than a bare Sienna system carries (at minimum `horizon_year`; verified via a
real `PLEXOSExporter.run()` call, which raised `PluginError: ... requires 'horizon_year' in
config to create simulation configuration` without it). Failures are reported in the
`xml_export` field of the tool's response rather than raised, so the System-level translation
(which always succeeds independent of PLEXOS-specific config) is still returned.

## `run_sienna_solve` -- real-install verification

`run_sienna_solve`'s Julia driver script (`sienna_mcp/scripts/solve_system.jl`) was run for
real during development of this connector, not just mocked:

- Julia 1.10.9, `PowerSystems.jl 5.12.1`, `PowerSimulations.jl 0.38.2`, `HiGHS.jl 1.24.1`,
  `JSON3.jl` -- installed fresh via `Pkg.add` into a scratch depot (~200s to precompile 206
  packages).
- A minimal native Sienna system (one `ACBus`, one `ThermalStandard` with a linear cost curve,
  one `PowerLoad` with an hourly load-shape `SingleTimeSeries`) was built directly in Julia and
  serialized with `PowerSystems.to_json`.
- The driver script loaded it, called `PowerSystems.transform_single_time_series!` (turns the
  attached `SingleTimeSeries` into the `Deterministic` forecast windows
  `PowerSimulations.DecisionModel` requires -- omitting this step fails with `"The System does
  not contain any forecast data or transformed time series data."`), built a minimal
  copper-plate `ProblemTemplate` (`ThermalBasicDispatch` / `RenewableFullDispatch` /
  `StaticPowerLoad`, whichever component types are present), and solved a 24-hour
  economic-dispatch problem with the open-source HiGHS solver.
- Real result: `build_status=BUILT`, `solve_status=SUCCESSFULLY_FINALIZED`,
  `objective_value=23039.999999999996`, solved in well under a second.

The automated test suite (`SIENNA/tests/test_tools.py::TestRunSiennaSolve`) mocks the Julia
subprocess rather than re-running this install (a multi-hundred-MB Julia toolchain is not
something CI should have to provision) -- the mocked tests check the Python-side subprocess
wiring, timeout handling, and result-JSON parsing; the real run above verified the Julia driver
script itself is correct against genuine Sienna packages.

## `compare_solutions`

Each of `sienna_path`/`plexos_path` may be either an R2X System JSON (compared by
component-type counts via `r2x_core.System.from_json`) or a plain results JSON, e.g.
`run_sienna_solve`'s own output (compared by shared numeric top-level fields). `r2x`/
`plexosdb` (an `r2x` transitive dependency) do not expose a PLEXOS *solution* reader as of
`r2x 2.1.0`/`plexosdb 1.5.0` -- only PLEXOS input-database CRUD (the surface `PLEXOSDB`, #53,
wraps) -- so the PLEXOS side of a results-vs-results comparison has to come from some other
export, not a call this connector makes into `r2x` itself.

## Tests

```bash
pytest SIENNA/tests -q
```

`SIENNA/tests/test_tools.py` mocks `r2x_core`/`r2x_plexos`/`r2x_sienna_to_plexos` via
`sys.modules` (PSCAD's `MagicMock` style) for `load_system`, `translate_to_plexos`, and
`compare_solutions`, and mocks the Julia subprocess for `run_sienna_solve`. A separate
license-free import test lives in the repo root's `tests/test_vendor_import.py`
(`test_sienna_main_import_and_server_creation_are_r2x_free`), extending its PSSE/PSLF pattern:
importing `sienna_mcp.main` and building the server must not import any `r2x` module, verified
in an environment where `r2x` is genuinely not installed.
