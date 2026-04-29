# reliability-assessment
Reliability Assessment Module

## What is NARP?
NARP is a power-system reliability assessment program originally developed in Fortran and ported to Python.
It evaluates resource adequacy for transmission systems using sequential Monte Carlo simulation.

Key indices:
- LOLE (Loss of Load Expectation): expected frequency of supply shortfall events.
- HLOLE (Hourly LOLE): expected number of shortfall hours.
- EUE (Expected Unserved Energy): expected amount of unmet energy demand.

In practice, engineers use these metrics for long-term planning, maintenance strategy evaluation, and adequacy studies.

## PowerMCP Integration

Within the PowerMCP repository, the MCP entry point is exposed via `NARP/narp_mcp.py`.
Run `python -m NARP.narp_mcp` to launch one FastMCP server with tools such as `submit_simulation`, `run_simulation_sync`, `validate_input`, and `get_job_summary`.

This integration follows the same registration pattern used by other PowerMCP integrations and builds on the upstream Python port at [zylpascal/NARP](https://github.com/zylpascal/NARP).

## Minimal bundled case files

To keep this integration branch clean, the repository now includes one minimal runnable case:
- `NARP/examples/case1`

The case contains the required input artifacts used by `validate_input`:
- `ZZMC.csv`, `ZZUD.csv`, `ZZLD.csv`, `ZZTD.csv`, `ZZTC.csv`, `LEEI`

For full benchmark and regression datasets, use the upstream NARP repository.

## Using NARP with PowerMCP

### Start the server

```bash
python -m NARP.narp_mcp
```

### Example prompts for MCP clients

- "List the available NARP tools and summarize each one."
- "Validate `NARP/examples/case1` before running the study."
- "Run a synchronous NARP simulation for `NARP/examples/case1` and return the TABLE 12/13 summary."
- "Submit an asynchronous NARP job for `NARP/examples/case1`, then monitor until completion."

After completion, inspect `output_python.txt` and `run.log` in `NARP/mcp_jobs/<job_id>/`.

## Contacts

- Shan Yang - yangsh237@mail2.sysu.edu.cn
- Yongli Zhu - yzhu16@alum.utk.edu
