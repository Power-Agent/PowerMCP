# HOPE MCP Server

This package provides a small stdio MCP server for local [HOPE](https://github.com/HOPE-Model-Project/HOPE) workflows in Claude Desktop.

## Tools

- `hope_case_info`
- `hope_run_hope`
- `hope_output_summary`

The v1 server intentionally supports only one whitelisted case id:

- `md_gtep_clean` -> `<HOPE_REPO_ROOT>/ModelCases/MD_GTEP_clean_case`

## One-time setup

1. Sync the Python package with `uv` (run inside `tools/hope_mcp_server`):

```bash
uv sync
```

2. Make sure the HOPE Julia environment is instantiated:

```bash
julia --project=/path/to/HOPE -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
```

## Claude Desktop config

Add this server entry to your Claude Desktop MCP config.

### Mac/Linux
Config location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hope": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/HOPE/tools/hope_mcp_server",
        "run",
        "hope-mcp-server"
      ],
      "env": {
        "HOPE_REPO_ROOT": "/absolute/path/to/HOPE",
        "HOPE_JULIA_BIN": "/absolute/path/to/julia/bin/julia"
      }
    }
  }
}
```

### Windows
Config location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hope": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\absolute\\path\\to\\HOPE\\tools\\hope_mcp_server",
        "run",
        "hope-mcp-server"
      ],
      "env": {
        "HOPE_REPO_ROOT": "C:\\absolute\\path\\to\\HOPE",
        "HOPE_JULIA_BIN": "C:\\absolute\\path\\to\\julia\\bin\\julia.exe"
      }
    }
  }
}
```

> **Note**: If `julia` is already successfully added to your system `PATH`, you can omit the `HOPE_JULIA_BIN` key from the `env` section.

## Local run

If running from outside the directory:

```bash
HOPE_JULIA_BIN=/absolute/path/to/julia/bin/julia \
uv --directory /absolute/path/to/HOPE/tools/hope_mcp_server run hope-mcp-server
```

Or, if `julia` is in your `PATH` and you run from within `tools/hope_mcp_server`:

```bash
uv run hope-mcp-server
```

## Test

```bash
uv --directory /absolute/path/to/HOPE/tools/hope_mcp_server run \
  python -m unittest discover -s tests -v
```
