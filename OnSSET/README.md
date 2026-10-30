# OnSSET MCP server

An MCP server that lets an AI client run the [OnSSET](https://github.com/OnSSET/onsset) geospatial
electrification model: find and validate inputs, calibrate a settlement file, run least-cost
electrification scenarios and analyse the results.

It drives the real OnSSET code: the `onsset` package of an unmodified clone of the upstream
repository. The calibration and scenario logic of the OnSSET notebooks is ported to two headless
scripts. The Uganda regression test shows the scenario script reproduces a notebook run.

## OnSSET version

The server is built and validated against one upstream commit:

| | |
|---|---|
| repository | [OnSSET/onsset](https://github.com/OnSSET/onsset), branch `master` |
| commit | [`486c26039ecbf8614d68da90c7b4968b2f4a5b13`](https://github.com/OnSSET/onsset/commit/486c26039ecbf8614d68da90c7b4968b2f4a5b13) ("Updated env files", 2026-06-29) |
| `git describe` | `ol-v2.0-30-g486c260` |
| package version | `onsset 2.1.dev30+g486c260…` (from `setuptools_scm`) |

No change to the OnSSET code is needed. The ports and the input checks follow these files at that
commit:

| upstream file | ported or mirrored in |
|---|---|
| `onsset/onsset.py`, `onsset/hybrids.py`, `onsset/hybrids_wind.py` | imported as-is by both engine scripts. `onsset_inputs.py` mirrors the columns and file layouts they read |
| `1. OnSSET_Calibration.ipynb` | `onsset_calibration.py` |
| `2. OnSSET_Scenarios.ipynb`, `funcs.ipynb`, `detailed_tech_parameters.ipynb` | `onsset_engine.py`, defaults in `onsset_params.py` |

The notebooks are not read at run time. Editing them in your checkout does not change what the
server computes. Changes to the `onsset` package do. `check_environment` returns the checkout's
`onsset_commit` next to `validated_against_commit`. If they differ, the checkout has moved away from
the validated commit: re-run the regression tests before trusting results.

## Architecture

```
MCP client ──stdio──▶ onsset_mcp.py           tools, argument checks, error boundary
                        ├─ onsset_config.py      paths, env vars, path containment, run names
                        ├─ onsset_params.py      pydantic schemas: ScenarioParams, CalibrationParams
                        ├─ onsset_inputs.py      input file validation (mirrors what OnSSET reads)
                        ├─ onsset_jobs.py        background runs: one subprocess per run
                        └─ onsset_results.py     reads run outputs (summary, breakdowns, comparisons)
                                 │ subprocess (ONSSET_PYTHON)
                                 ▼
                       onsset_calibration.py  ── port of 1. OnSSET_Calibration.ipynb ──┐
                       onsset_engine.py       ── port of 2. OnSSET_Scenarios.ipynb ────┤──▶ onsset package
                                                 + funcs.ipynb, detailed_tech_parameters  (OnSSET clone @ 486c260)
```

The server process never imports `onsset`:

* OnSSET prints its progress to stdout, and over stdio, stdout is the MCP protocol channel.
* A national run takes minutes and several GB of memory.

Calibration and scenario runs are therefore started as subprocesses. Each run gets its own folder in
the workspace, and the client polls it with `get_run_status`. The subprocess gets no stdin and writes
stdout and stderr to `engine.log`. Run status comes from files (`job.json` and `<name>_Run.json`), so a
restarted server can still report on earlier runs. When the server exits, it terminates the runs it
started and marks them `cancelled`.

Run folder layout (`<workspace>/<name>/`):

| file | written by | content |
|---|---|---|
| `job.json` | server | kind, inputs, command, pid, status, start/end time |
| `params.json` | server | complete validated parameters given to the engine |
| `engine.log` | engine | OnSSET progress output |
| `<name>_Run.json` | engine | result: status, rates, summary, file paths, timing (or the error) |
| `<name>_Results.csv` | scenario | settlement-level results, one row per settlement |
| `<name>_Summaries.csv` | scenario | population, connections, capacity, investment, emissions per technology |
| `<name>_Params.json` | scenario | parameters, inputs and start-year statistics |
| `new_mv_lines_<name>_<year>.geojson` | scenario | new MV lines per time step (EPSG:4326) |
| `OnSSET_InputFile_Calibrated.csv` | calibration | calibrated settlements, the input of scenario runs |

## Prerequisites and installation

1. A clone of OnSSET at the validated commit.
2. A Python environment with OnSSET's dependencies plus `mcp>=2,<3` and `pytest`.
   `onsset_env_mcp.yml` describes it.

The commands below use these placeholders:

| placeholder | meaning | example |
|---|---|---|
| `<onsset>` | your OnSSET clone | `C:\Users\me\onsset` |
| `<PowerMCP>` | this repository | `C:\Users\me\PowerMCP` |
| `<env-python>` | `python.exe` of the conda environment | `C:\Users\me\anaconda3\envs\onsset_env_mcp\python.exe` |

```powershell
git clone https://github.com/OnSSET/onsset.git <onsset>
git -C <onsset> checkout 486c26039ecbf8614d68da90c7b4968b2f4a5b13
conda env create -f <PowerMCP>\OnSSET\onsset_env_mcp.yml
conda activate onsset_env_mcp
pip install -e <onsset>      # installs the onsset package from your clone
```

The `checkout` leaves the clone on a detached HEAD. That is intended: it keeps the clone at the
validated commit. To try a newer OnSSET, check out that commit instead and run the tests (see
[Tests](#tests)).

`pip install -e` is required for the default configuration. With it, the engine interpreter finds
the clone by itself, and `ONSSET_REPO` can stay unset.

The engine is checked against the versions in that environment: Python 3.12, pandas 3.0, numpy 2.4,
geopandas 1.1, numba 0.65, mcp 2.2.

This server deliberately does not depend on the `powermcp` package. PowerMCP's core dependencies pin
`pandas<3`, which would downgrade the environment that OnSSET was validated in.

## Configuration

Every setting is an environment variable read at call time. Nothing has to be set on a machine
where OnSSET is installed in editable mode.

| variable | default | purpose |
|---|---|---|
| `ONSSET_REPO` | the checkout the engine interpreter imports `onsset` from | example data and notebooks. Relative input paths resolve against it |
| `ONSSET_PYTHON` | the interpreter running the server | interpreter for the engine subprocesses |
| `ONSSET_WORKSPACE` | `OnSSET\runs` (git-ignored) | one folder per run |
| `ONSSET_ALLOWED_ROOTS` | none | extra input folders, separated by `;` on Windows |
| `ONSSET_MAX_CONCURRENT_RUNS` | `1` | parallel engine processes |
| `ONSSET_MCP_LOG_LEVEL` | `INFO` | server log level (logs go to stderr) |

Tools read input files only from the OnSSET repo, the workspace and `ONSSET_ALLOWED_ROOTS`. Paths
are resolved, including `..` and symlinks, before that check. Tools write only inside
`<workspace>/<run name>`. A run name is 1–64 characters from letters, digits, `_`, `-` and `.`.

## Launching

```powershell
<env-python> <PowerMCP>\OnSSET\onsset_mcp.py
```

The server speaks MCP over stdio, so it waits silently for a client.

### Claude Code

```powershell
claude mcp add onsset -- <env-python> <PowerMCP>\OnSSET\onsset_mcp.py
```

### Claude Desktop and other JSON-configured clients

```json
{
  "mcpServers": {
    "onsset": {
      "command": "C:\\Users\\me\\anaconda3\\envs\\onsset_env_mcp\\python.exe",
      "args": ["C:\\Users\\me\\PowerMCP\\OnSSET\\onsset_mcp.py"],
      "env": {
        "ONSSET_REPO": "C:\\Users\\me\\onsset",
        "ONSSET_ALLOWED_ROOTS": "C:\\Users\\me\\Documents\\onsset_data"
      }
    }
  }
}
```

Use the environment's own `python.exe`. A bare `python` would start whichever interpreter is first
on `PATH`. In JSON, write backslashes as `\\` or use forward slashes.

## Tools

All tools return structured JSON. Expected failures come back as MCP tool errors (`isError: true`)
with a readable message: invalid parameters, missing files, paths outside the allowed roots, unknown
runs. The server keeps serving after any tool error.

| tool | purpose |
|---|---|
| `get_server_info` | version, repo, workspace, engine interpreter, allowed roots, limits |
| `check_environment` | imports OnSSET and its dependencies in the engine interpreter; versions, git commit, problems |
| `list_input_files(directory?, max_depth=3)` | candidate inputs with detected role (calibrated or GIS settlements, PV, wind, MV lines); default `<repo>\test` |
| `describe_parameters(workflow="scenario")` | every parameter of `scenario` or `calibration`: group, unit, default, constraints |
| `validate_parameters(params, workflow="scenario")` | complete parameter set with defaults and model time steps, or the list of errors |
| `validate_inputs(input_csv, workflow, pv_csv?, wind_csv?, mv_lines?, params?)` | checks the input files (see below) |
| `start_calibration(input_csv, params, run_name, overwrite=false, validate=true)` | calibrates a GIS-extracted CSV in the background |
| `start_scenario_run(input_csv, pv_csv, wind_csv, mv_lines, params, scenario_name, overwrite=false, validate=true)` | runs a scenario in the background |
| `get_run_status(run_name, log_lines=20)` | `running`, `succeeded`, `failed`, `cancelled` or `interrupted`; elapsed time, error, log tail |
| `cancel_run(run_name)` | stops a run started by this server |
| `list_runs()` | every run in the workspace with its status |
| `get_run_results(run_name)` | scenario: rates per year, start-year stats, summary per technology, files. Calibration: base-year statistics and the calibrated CSV |
| `inspect_result_columns(run_name)` | settlement count and per-year metrics of the results CSV, with units |
| `summarize_results_by(run_name, group_by, year?, max_groups=50)` | population, connections, capacity and investment per group (e.g. `Admin_1`, `IsUrban`) and technology |
| `compare_runs(run_names)` | final rates, per-technology totals and differing parameters of two or more runs |

`overwrite=true` deletes the existing run folder of that name. Without it, starting a run with an
existing name is refused.

### What `validate_inputs` checks

The checks follow the OnSSET code (`onsset/onsset.py`, `hybrids.py`, `hybrids_wind.py`):

* **Settlements CSV.** Read like `SettlementProcessor`: `,` separator, or `;` when that is the only
  way to find `GHI`.
  * Always required: `id, X_deg, Y_deg, Pop, GridCellArea, GHI`.
  * A scenario also needs the calibration outputs `PopStartYear, ElecPopCalib, ElecStart, IsUrban,
    WindCF, FinalElecCode<start_year>, ElecPop<start_year>`. Without `start_year` in `params`, the
    latest `FinalElecCode<year>` column sets it.
  * Errors: empty or non-numeric values, duplicate ids, coordinates outside WGS84 ranges, negative
    populations, unknown `FinalElecCode` values, no urban settlement, and an `end_year_pop` below the
    start-year population (OnSSET would then report rates above 100%).
  * Warnings: columns OnSSET fills with 0 or 9999 itself.
  * Calibration additionally needs `NightLights` and a grid-distance column. It also needs `MGDist`
    unless `mg_dist` is 0: OnSSET would fill a missing `MGDist` with 0 and mark every un-gridded
    settlement as mini-grid electrified.
* **PV CSV.** OnSSET skips the first 341,882 lines and reads temperature (column 2) and surface
  irradiance (column 3) of the remaining 8,760 hours. That means the full renewables.ninja country
  weather file for 1980–2019, of which it uses the last year.
* **Wind CSV.** A renewables.ninja wind point file: 3 comment lines, then 8,760 wind speeds in
  column 3 (`wind_speed`).
* **MV lines.** A vector file with (Multi)LineStrings and a CRS. A warning is raised if it does not
  overlap the settlements.

### Example session

The session uses the Uganda inputs described in [Test data](#test-data).

1. `check_environment` returns `{"ok": true, "packages": {"onsset": "2.1.dev30+g486c26039…", …},
   "onsset_commit": "486c260…", "validated_against_commit": "486c260…"}`.
2. `list_input_files` lists `test\inputTestUganda\OnSSET_InputFile_Calibrated_v1.csv`
   (`settlements (calibrated)`), `ug-2-pv.csv`, `ug-2-wind.csv` and `UGA\UGA\UGA_mv_lines.shp`.
3. `validate_parameters` with
   ```json
   {"params": {"start_year": 2024, "end_year": 2050, "end_year_pop": 86000000,
               "urban_ratio_end_year": 0.36, "intermediate_targets": {"2030": 0.6}}}
   ```
   returns `"valid": true` and the time steps `[{"year": 2030, "electrification_target": 0.6, "step_years": 6},
   {"year": 2050, "electrification_target": 1.0, "step_years": 20}]`.
4. `validate_inputs` with
   ```json
   {"input_csv": "test/inputTestUganda/OnSSET_InputFile_Calibrated_v1.csv",
    "pv_csv": "test/inputTestUganda/ug-2-pv.csv", "wind_csv": "test/inputTestUganda/ug-2-wind.csv",
    "mv_lines": "test/inputTestUganda/UGA/UGA/UGA_mv_lines.shp", "params": {"start_year": 2024}}
   ```
   returns `"ok": true`, 397,910 settlements and a start-year electrification rate of 0.350.
5. `start_scenario_run` with the same files, the parameters from step 3 and
   `"scenario_name": "uganda_2050"`. Then call `get_run_status {"run_name": "uganda_2050"}` until the
   status is `succeeded` (about 3–5 minutes nationally).
6. `get_run_results {"run_name": "uganda_2050"}` returns `summary_by_technology`, keyed by
   `Grid_dens, Grid_ext, SA_PV, MG_PV_Hybrid, MG_Wind, MG_Hydro, Non-electrified, Total`. Each entry
   has columns such as `Population2050`, `NewConnections2050`, `Capacity2050 (MW)`,
   `Investment2050 (million USD)` and `Emissions2050 (ktCO2)`. Multi-step runs add `...Total` columns.
7. `summarize_results_by {"run_name": "uganda_2050", "group_by": "Admin_1"}` gives a regional
   breakdown. `compare_runs {"run_names": ["uganda_2050", "uganda_cheap_pv"]}` gives scenario deltas.

For a GIS extract that is not yet calibrated, first run
`describe_parameters {"workflow": "calibration"}` and then `start_calibration`. Its
`get_run_results` reports the path of `OnSSET_InputFile_Calibrated.csv`, which is the `input_csv`
of the scenario.

### Interpreting results

* `FinalElecCode<year>`: 1 = grid densification (already connected in the start year), 2 = grid
  extension, 3 = stand-alone PV, 5 = PV-hybrid mini-grid, 6 = wind mini-grid, 7 = hydro mini-grid,
  99 = not electrified.
* Summary capacity (MW), investment (million USD) and emissions (ktCO2/year) are what is added in
  each period. The `Total` columns of multi-step runs sum the periods. The notebook labels emissions
  `tCO2`, but the values are kt.
* Settlement-level units: `NewCapacity` is kW, `InvestmentCost` is USD, `NewConnections` is
  households and `Pop` is people.
* PV-hybrid mini-grids are sized with an unseeded differential evolution in OnSSET. Two runs with
  identical inputs can differ slightly in capacity and investment, but not in technology choice or
  population.

## Command-line use without MCP

```powershell
python onsset_calibration.py --input-csv in.csv --params calib.json --output-dir out --name c1
python onsset_engine.py --input-csv calibrated.csv --pv-csv pv.csv --wind-csv wind.csv `
    --mv-lines mv.shp --params params.json --output-dir out --scenario-name s1
```

## Test data

Two datasets are used. Only the first ships with the upstream repository.

* **Djibouti** (`<onsset>\test\test_data\dj-test.csv`) is tracked in OnSSET at `486c260`. It is an
  uncalibrated GIS extract, and the slow stdio test calibrates it.
* **Uganda** is not part of the OnSSET repository. Place it in the clone, untracked, as:

  ```
  <onsset>\test\inputTestUganda\OnSSET_InputFile_Calibrated_v1.csv   calibrated settlements, 397,910 rows
  <onsset>\test\inputTestUganda\ug-2-pv.csv                         renewables.ninja weather, 1980-2019
  <onsset>\test\inputTestUganda\ug-2-wind.csv                       renewables.ninja wind
  <onsset>\test\inputTestUganda\UGA\UGA\UGA_mv_lines.shp            existing MV lines (+ .dbf .shx .prj .cpg)
  <onsset>\test\outputTestUganda\ugandaGeneral_*.csv, new_mv_lines_ugandaGeneral_2050.geojson
  ```

  `tests/baseline_uganda/inputs.json` records the size and SHA-256 of every input. Compare them
  to confirm you have the same files.

The reference outputs in `outputTestUganda` come from the upstream `2. OnSSET_Scenarios.ipynb` at
`486c260`, run on the Uganda inputs. The notebook was changed in two cells only:

| notebook cell | upstream value | reference run |
|---|---|---|
| `end_year` | `2030` | `2050` |
| `end_year_pop` | `26000000` | `86000000` |

All other inputs keep the notebook defaults. `tests/baseline_uganda/params.json` contains the full
parameter set.

The GIS extraction notebook is a separate upstream repository,
[OnSSET/OnSSET_GIS_Extraction_notebook](https://github.com/OnSSET/OnSSET_GIS_Extraction_notebook).
The server does not use it (see [Limitations](#limitations)).

## Tests

```powershell
cd <PowerMCP>\OnSSET
<env-python> -m pytest tests -m "not slow" --ignore=tests/test_baseline_uganda.py   # ~15 s
<env-python> -m pytest tests/test_mcp_stdio.py -m slow                               # ~3 min, real model through MCP
<env-python> -m pytest tests/test_baseline_uganda.py                                 # ~3 min, national notebook regression
```

| file | covers |
|---|---|
| `test_params.py` | parameter schemas, defaults, constraints, time horizon |
| `test_inputs.py` | every validator on synthetic files, plus the real Uganda inputs when present |
| `test_jobs.py` | run lifecycle with a stand-in engine: success, failure, crash, overwrite, concurrency, cancel, restart |
| `test_results.py` | summary, columns, breakdown, comparison, missing and failed runs |
| `test_server.py` | tool registration and schemas, error mapping, path containment |
| `test_mcp_stdio.py` | real stdio sessions: protocol, errors, recovery. `slow`: calibration (Djibouti) and two scenarios plus a cancel on a 4,385-settlement Uganda window |
| `test_baseline_uganda.py` | the engine reproduces the national Uganda notebook run |

The data-dependent tests skip when the test data is absent. They look in
`C:\Users\corra\Desktop\onsset` by default. Set `ONSSET_UGANDA_REPO=<onsset>` to point them at
your clone.

Run all three after moving the clone to another OnSSET commit. `test_baseline_uganda.py` is the one
that detects a change in model results.

## Limitations

* Only the notebook workflows are exposed: calibration and scenario runs. GIS extraction
  (`OnSSET_GIS_Extraction_notebook`), the older Excel-driven `onsset/runner.py` and the plots are not.
* Productive-use demand, per-settlement grid reliability and the notebooks' "simplified results"
  export are not parameters. The values fixed in `detailed_tech_parameters.ipynb` (O&M shares,
  efficiencies, lifetimes not listed in `describe_parameters`) are kept as in the notebook.
* The PV file must have the 1980–2019 renewables.ninja layout, because OnSSET hard-codes the row
  offset.
* Like the notebook, the grid seeds are the existing MV lines plus the settlements connected in the
  latest `FinalElecCode<year>` column.
* `cancel_run` only stops runs started by the current server process. A run left by a crashed
  server shows as `interrupted`.
* Runs are not resumable. A cancelled run keeps its partial folder until it is overwritten.

## Troubleshooting

* `check_environment` reports a different `onsset_commit` from `validated_against_commit`. Run
  `git -C <onsset> checkout 486c26039ecbf8614d68da90c7b4968b2f4a5b13`, or run the tests against the
  new commit.
* `check_environment` reports `onsset` as not importable. Point `ONSSET_PYTHON` at the environment
  where `pip install -e <onsset>` was run.
* "outside the allowed directories": add the input folder to `ONSSET_ALLOWED_ROOTS`.
* A run `failed`: `get_run_status` returns the engine's error message and the last log lines. The
  full log is `engine.log` in the run folder.
* "already in progress": only `ONSSET_MAX_CONCURRENT_RUNS` runs may execute at once.
* GDAL prints `GDAL_DATA is not defined` warnings to the engine log. They are harmless for the
  formats used here.

## Acknowledgements

We thank:

* the Department of Energy of Politecnico di Milano, represented by Marco Merlo and Andrea Pomarico;
* the Division of Energy Systems at KTH Royal Institute of Technology, in the person of
  Francesco Fuso Nerini.
