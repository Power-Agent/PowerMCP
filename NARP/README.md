# NARP — PowerMCP connector

This is a thin connector for the Breakthrough Energy
[reliability-assessment](https://github.com/Breakthrough-Energy/reliability-assessment)
project, which ports the NARP power-system reliability assessment program to
Python.

PowerMCP does not vendor the NARP implementation. Install the upstream package
separately from its source repository:

```bash
pip install "reliabilityassessment @ git+https://github.com/Breakthrough-Energy/reliability-assessment.git"
```

Then run:

```bash
powermcp run narp
```

The connector calls NARP's public narpMain(TEST_DIR) function in a child Python
process rather than executing narpMain.py as a script. The upstream module
defines the function but has no __main__ launcher.

## Input

The current NARP input pipeline reads all of these artifacts:

- ZZTC.csv
- ZZMC.csv
- ZZLD.csv
- ZZUD.csv
- ZZTD.csv
- ZZFC.csv
- ZZOD.csv
- ZZDD.csv
- LEEI

## MCP tools

- ping
- validate_input
- submit_simulation
- run_simulation_sync
- get_job_status
- get_job_result
- get_job_summary
- list_jobs
- cancel_job

The job manager persists job metadata under PowerMCP's generated run directory.
Jobs that were pending/running when the MCP server stopped are restored as
failed with an explicit restart error rather than disappearing.

The summary parser keeps TABLE 12's GC/TC/GT/AV rows, retains the MAGN and
percentage-standard-deviation columns from TABLE 13, and preserves pool
statistics.

The upstream project is MIT licensed. PowerMCP does not redistribute that
implementation; the upstream repository remains the installation source.
