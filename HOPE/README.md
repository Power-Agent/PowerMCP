# HOPE MCP Server

This package provides two MCP server entrypoints for the HOPE Julia repository:

- `hope-mcp-server`
  - local full-access `stdio` server for Claude Desktop
- `hope-mcp-server-chatgpt`
  - remote read-only `streamable-http` server for ChatGPT web developer mode

Both variants resolve cases dynamically from `ModelCases/` by looking for
`Settings/HOPE_model_settings.yml`.

## Tool split

Claude/local full-access server:

- `hope_warmup`
- `hope_job_status`
- `hope_cancel_job`
- `hope_debug_solver_environment`
- `hope_debug_solver_environment_async`
- `hope_case_info`
- `hope_output_summary`
- `hope_run_hope`
- `hope_update_settings`
- `hope_validate_case`
- `hope_read_output`
- `hope_emission_compliance`
- `hope_nodal_prices`
- `hope_compare_cases`
- `hope_run_holistic`
- `hope_run_erec`
- `hope_rep_day_audit`
- `hope_aggregation_audit`
- `hope_open_dashboard`
- `hope_close_dashboard`

ChatGPT remote read-only server:

- `hope_case_info`
- `hope_output_summary`
- `hope_validate_case`
- `hope_read_output`
- `hope_emission_compliance`
- `hope_nodal_prices`
- `hope_compare_cases`
- `hope_rep_day_audit`
- `hope_aggregation_audit`

## One-time setup

1. Sync the Python package with `uv`:

```bash
uv --directory /path/to/HOPE/tools/hope_mcp_server sync
```

2. Make sure the HOPE Julia environment is instantiated:

```bash
julia --project=/path/to/HOPE -e "using Pkg; Pkg.instantiate(); Pkg.precompile()"
```

3. Optional but recommended for agent-controlled runs: verify the active HOPE environment
   and solver setup before the first model launch:

```bash
julia --project=/path/to/HOPE /path/to/HOPE/tools/repo_utils/agent_preflight_check.jl \
  ModelCases/MD_GTEP_clean_case
```

For commercial solvers, the preflight script checks both package loading and solver
initialization. Example:

```bash
julia --project=/path/to/HOPE /path/to/HOPE/tools/repo_utils/agent_preflight_check.jl \
  ModelCases/MD_GTEP_clean_case --solver gurobi
```

## Claude Desktop config

Add this server entry to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "hope": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/HOPE/tools/hope_mcp_server",
        "run",
        "hope-mcp-server"
      ],
      "env": {
        "HOPE_REPO_ROOT": "/path/to/HOPE",
        "HOPE_JULIA_BIN": "/path/to/julia",
        "JULIA_DEPOT_PATH": "/path/to/julia_depot"
      }
    }
  }
}
```

## ChatGPT read-only remote server

Start the read-only server locally on your machine:

```bash
HOPE_REPO_ROOT=/path/to/HOPE \
HOPE_MCP_PUBLIC_HOSTNAME=hope.example.com \
HOPE_MCP_HOST=127.0.0.1 \
HOPE_MCP_PORT=8001 \
uv --directory /path/to/HOPE/tools/hope_mcp_server run hope-mcp-server-chatgpt
```

Important notes:

- This entrypoint uses FastMCP `streamable-http`.
- It is intended for ChatGPT web developer mode, not Claude Desktop.
- It does not expose case-running or settings-writing tools.
- If you publish the service behind Cloudflare Tunnel or another reverse proxy,
  set `HOPE_MCP_PUBLIC_HOSTNAME` to the public hostname so FastMCP accepts the
  forwarded `Host` header.
- ChatGPT currently requires a remote HTTPS-reachable MCP endpoint, so you will
  typically place a tunnel or reverse proxy in front of this local process.

Suggested exposure options:

- Cloudflare Tunnel
- Tailscale Funnel
- a reverse proxy on your own HTTPS domain

## Case IDs

Both servers accept:

- exact `ModelCases` directory names such as `USA_64zone_GTEP_case`
- prefixed paths such as `ModelCases/USA_64zone_GTEP_case`
- the legacy alias `md_gtep_clean`

## Local run

Full local server:

```bash
uv --directory /path/to/HOPE/tools/hope_mcp_server run hope-mcp-server
```

Read-only remote server:

```bash
HOPE_REPO_ROOT=/path/to/HOPE \
HOPE_MCP_PUBLIC_HOSTNAME=hope.example.com \
HOPE_MCP_PORT=8001 \
uv --directory /path/to/HOPE/tools/hope_mcp_server run hope-mcp-server-chatgpt
```

## Test

```bash
uv --directory /path/to/HOPE/tools/hope_mcp_server run \
  python -m unittest discover -s tests -v
```

If an agent launches a long-running Julia job and needs to stop it early, call
`hope_cancel_job(job_id)` with the `job_id` returned by `hope_warmup`,
`hope_run_hope`, `hope_run_holistic`, or `hope_run_erec`.

If Claude appears to be running stale code or the wrong Julia environment, call
`hope_debug_solver_environment(case_id, solver, timeout_seconds)` to inspect the active project,
depot path, loaded `HOPE.jl` path, and the exact optimizer constructor JuMP sees.

If the synchronous debug probe risks hitting Claude-side request timeouts, call
`hope_debug_solver_environment_async(case_id, solver)` and then poll with
`hope_job_status(job_id)` to retrieve the full probe stdout, stderr, and parsed fields.

## Dashboard launch notes

The `hope_open_dashboard` tool launches the HOPE dashboards from the repository
root and, on Windows, intentionally shells out through `cmd.exe /d /c` instead
of invoking Python directly. This mirrors the manual Command Prompt launch path
that has proven reliable with Claude Desktop and the local MCP server.

The tool also:

- sanitizes inherited Python environment variables that can interfere with Dash startup
- sets `HOPE_MODELCASES_PATH` so the dashboard can discover `ModelCases/`
- sets `HOPE_DASHBOARD_PORT` so the runner scripts can bind the requested port
- writes startup logs to `tools/hope_dashboard/logs/`

If `hope_open_dashboard` reports a startup timeout or immediate crash, check the
returned `log_path` first.
