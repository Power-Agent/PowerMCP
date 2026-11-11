# PowerMCP: installation guide for AI agents

This file is written for an AI coding agent (Claude Code, Codex, Cursor, Cline, or
similar) that a user has asked to install and configure PowerMCP. Humans can follow
it too, but the [README](README.md) is the shorter read.

**Goal:** install the `powermcp` Python package with the power-system tools the user
wants, store the local paths of any vendor software, register one MCP server per tool
in the user's MCP client(s), and verify that the servers start.

Work through the steps in order. Every command is non-interactive and safe to run from
an agent shell, which has no TTY.

## Ground rules

1. **Ask once, up front, for what you can't find out.** If the user's request doesn't
   already say, ask in a single message:
   - which tools they want (the core tools pandapower, PyPSA and PowerIO are always
     installed; see the table in step 3),
   - which MCP clients to configure (`claude-code`, `claude-desktop`, `codex`, or
     another client),
   - the install path of any commercial software you can't locate yourself (step 4).
2. **Don't install into the system Python** and don't use `sudo`. Use a dedicated
   virtual environment (step 2).
3. **Commercial software is the user's to install.** PSS/E, PSLF, PowerFactory,
   PowerWorld, PSCAD and LTspice must already be installed and licensed on this
   machine. Never download vendor installers or enter license details.
4. **Leave the user's other MCP servers alone.** The installer only adds, updates or
   removes entries whose names start with `powermcp_`, and it backs up each client
   config file once (`*.powermcp.bak`) before its first write.
5. **Use one interpreter throughout.** The client config records the absolute path of
   the Python interpreter that ran `powermcp install`. Run every command below through
   that same interpreter, written `"$PY" -m ...` in this guide.

## Step 1: check the environment

```bash
uname -a 2>/dev/null || ver          # OS
python3 --version                    # macOS / Linux
py -0p                               # Windows: lists every installed Python
```

- Python **3.10 to 3.14** is supported. Prefer **3.12 or 3.13**, which every extra
  supports (`surge` needs 3.12 to 3.14; PLEXOSDB's `r2x` dependencies need 3.11
  to 3.13).
- **PSS/E and PowerFactory load a vendor Python module built for one Python version.**
  Match the venv to the vendor folder: `PSSPY311` needs Python 3.11, and
  `PowerFactory 2024\Python\3.11` needs Python 3.11.
- **Windows only:** `powerworld`, `psse`, `pslf`, `powerfactory`, `pscad`. On macOS
  or Linux the installer skips them with `Not available on this platform/Python`.
  Tell the user instead of trying to work around it.
- See which clients are present: `claude --version` (Claude Code),
  `codex --version` (Codex CLI), and the Claude Desktop config folder from step 5.

## Step 2: create a persistent virtual environment

The venv must survive: the MCP client launches the servers from it, so deleting or
moving it breaks them. Don't create it in a temporary or build directory. If the user
already has an environment they want to use (a conda env, a project venv), use that.

macOS / Linux:

```bash
python3.12 -m venv ~/.venvs/powermcp
PY="$HOME/.venvs/powermcp/bin/python"
"$PY" -m pip install --upgrade pip
```

Windows (PowerShell):

```powershell
py -3.12 -m venv "$env:USERPROFILE\.venvs\powermcp"
$PY = "$env:USERPROFILE\.venvs\powermcp\Scripts\python.exe"
& $PY -m pip install --upgrade pip
```

In PowerShell, run the later commands as `& $PY -m ...` instead of `"$PY" -m ...`.

With **uv** instead: `uv venv -p 3.12 ~/.venvs/powermcp`, then install with
`uv pip install --python "$PY" ...`. A uv venv has no `pip`, so never pass `--yes` to
`powermcp install` there (step 5 explains why).

## Step 3: install the package and the extras

Map each tool the user wants to its pip extra:

| Tool id | Software | pip extra | Platform | Also needs |
|---|---|---|---|---|
| `pandapower` | pandapower | *(core)* | any | |
| `pypsa` | PyPSA | *(core)* | any | HiGHS ships with the core install; CBC, GLPK or Gurobi optional |
| `powerio` | PowerIO case conversion | *(core)* | any | |
| `andes` | ANDES | `andes` | any | |
| `egret` | Egret | `egret` | any | an optimization solver on PATH (ipopt or Gurobi) |
| `opendss` | OpenDSS | `opendss` | any | |
| `surge` | surge | `surge` | any, Python 3.12+ | |
| `hope` | HOPE | `hope` | any | a HOPE.jl checkout and Julia (paths in step 4) |
| `genx` | GenX | `genx` | any | a GenX.jl checkout (path in step 4); SLURM `sbatch` to submit cases |
| `ltspice` | LTspice | `ltspice` | any | LTspice installed (executable auto-detected) |
| `plexosdb` | PLEXOS database | `plexosdb` | any, Python 3.11 to 3.13 | extra manual steps, see [PLEXOSDB/README.md](PLEXOSDB/README.md) |
| `powerworld` | PowerWorld Simulator | `powerworld` | Windows | a running, licensed Simulator |
| `psse` | PSS/E | `psse` | Windows | PSS/E installed (paths in step 4) |
| `pslf` | GE PSLF | `pslf` | Windows | PSLF installed (path in step 4) |
| `powerfactory` | DIgSILENT PowerFactory | `powerfactory` | Windows | PowerFactory installed (path in step 4) |
| `pscad` | PSCAD | `pscad-windows` | Windows | PSCAD installed |

Convenience extras: `opensource` (every open-source extra), `windows` (every Windows
vendor tool), `all` (everything).

Install the core package and the extras in one command. **Quote the brackets**;
zsh (the macOS default shell) otherwise rejects them:

```bash
"$PY" -m pip install "powermcp[andes,opendss]"     # core + ANDES + OpenDSS
"$PY" -m pip install powermcp                      # core tools only
```

Developers working from a clone of this repository install it in editable mode instead:
`"$PY" -m pip install -e ".[andes,opendss]"`.

Confirm the install: `"$PY" -m powermcp --version` and `"$PY" -m powermcp list`.

## Step 4: store vendor software paths (only for tools that need them)

Skip this step if the user picked only tools without paths (`pandapower`, `pypsa`,
`powerio`, `andes`, `egret`, `opendss`, `surge`, `powerworld`, `pscad`).

For each key below, look in the typical location first, confirm the path exists,
and ask the user only if you can't find it. Then store it:

```bash
"$PY" -m powermcp config set <tool>.<key> "<path>"
```

| Key | What it points to | Typical location |
|---|---|---|
| `psse.python_lib` | PSS/E `PSSPYxxx` folder matching the venv Python | `C:\Program Files\PTI\PSSE36\36.2\PSSPY311` |
| `psse.bin` | PSS/E `PSSBIN` folder | `C:\Program Files\PTI\PSSE36\36.2\PSSBIN` |
| `pslf.python_lib` | folder that contains the `PSLF_PYTHON` module | `C:\Program Files\GE PSLF\PSLF_PYTHON` |
| `powerfactory.python_path` | PowerFactory's Python folder matching the venv Python | `C:\Program Files\DIgSILENT\PowerFactory 2024\Python\3.11` |
| `ltspice.exe` | LTspice executable (normally auto-detected, so set it only when `doctor` reports it missing) | `C:\Program Files\ADI\LTspice\LTspice.exe` |
| `hope.repo_root` | root of the user's HOPE.jl checkout | ask the user |
| `hope.julia_bin` | Julia executable | output of `which julia` / `where julia` |
| `hope.julia_depot_path` | optional `JULIA_DEPOT_PATH` | leave unset unless the user has one |
| `genx.repo_root` | root of the user's GenX.jl checkout | ask the user |

The values live in `~/.powermcp/config.toml`; `"$PY" -m powermcp config show` prints it.

## Step 5: write the MCP client configuration

**5a. Find what's already configured.** Re-running the installer with `--tools`
removes every `powermcp_*` entry whose tool isn't in the list. Before writing, read the
existing entries and add those tools to your `--tools` list unless the user asked to
drop them:

| Client | Config file | Where PowerMCP's entries are |
|---|---|---|
| Claude Code | `~/.claude.json` | `mcpServers.powermcp_*` (or run `claude mcp list`) |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` | `mcpServers.powermcp_*` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` | `mcpServers.powermcp_*` |
| Claude Desktop (Linux) | `~/.config/Claude/claude_desktop_config.json` | `mcpServers.powermcp_*` |
| Codex CLI | `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`) | `[mcp_servers.powermcp_*]` tables |

**5b. Preview, then write.** `--tools` takes comma-separated tool ids; the core
tools are always added. `--clients` takes any of `claude-code`, `claude-desktop`,
`codex` (the default is all three); configure only the clients the user uses.

```bash
"$PY" -m powermcp install --tools andes,opendss --clients claude-code,codex --dry-run
"$PY" -m powermcp install --tools andes,opendss --clients claude-code,codex
```

Run from an agent shell, which has no TTY, `powermcp install --tools ...` skips the
checkbox picker, the path prompts and its own `pip install`, and only writes the client
config. Steps 3 and 4 already covered the rest, so that's what you want. Don't add
`--yes`: it makes the installer run `python -m pip install` itself, which fails in a
uv venv.

**Other MCP clients** (Cursor, VS Code, Windsurf, Cline, Gemini CLI and others) aren't
written by the installer. Add one stdio server per tool by following that client's
MCP documentation, with the absolute interpreter path as the command:

```json
{
  "mcpServers": {
    "powermcp_pandapower": {
      "command": "/Users/me/.venvs/powermcp/bin/python",
      "args": ["-m", "powermcp", "run", "pandapower"]
    }
  }
}
```

On Windows the command is the venv's `Scripts\python.exe`, with backslashes escaped in
JSON (`"C:\\Users\\me\\.venvs\\powermcp\\Scripts\\python.exe"`).

## Step 6 (optional): let the servers read the user's case folders

The servers read and write files only beneath their allowed roots. With no setting,
that's the directory the server process started in; for Claude Code and Codex this is
usually the project folder. If the user keeps cases elsewhere, ask which folders to
allow and set `POWERIO_MCP_ALLOWED_ROOTS` in the `env` of each `powermcp_*` entry
(separate folders with `:` on macOS/Linux, `;` on Windows):

```json
"powermcp_pandapower": {
  "command": "...",
  "args": ["-m", "powermcp", "run", "pandapower"],
  "env": { "POWERIO_MCP_ALLOWED_ROOTS": "/Users/me/cases:/Users/me/studies" }
}
```

In Codex's TOML, add `env = { POWERIO_MCP_ALLOWED_ROOTS = "/Users/me/cases" }` to each
`[mcp_servers.powermcp_*]` table. Re-running `powermcp install` rewrites the
`powermcp_*` entries and drops this `env` block, so add it again afterwards.

## Step 7: verify

```bash
"$PY" -m powermcp doctor           # every tool, or: "$PY" -m powermcp doctor psse
```

- **dependencies:** each selected tool shows `ok`. `missing; pip install powermcp[x]`
  means the extra isn't installed in this venv (go back to step 3).
- **config paths:** `set: <tool>.<key>` means a required path is still missing
  (go back to step 4).
- Windows-only tools show `skipped, Windows-only` on other platforms.
- The closing notes list tools that also need an external solver or runtime on PATH.

Then check that the client sees the servers:

- **Claude Code:** `claude mcp list` should list each `powermcp_*` server as connected.
- **Codex CLI:** `codex mcp list`.
- **Claude Desktop:** the user must fully quit Claude Desktop (from the menu bar or
  system tray, not just the window) and reopen it; **Settings > Developer** then shows
  each server's status.

Don't run `powermcp run <tool>` in the foreground to test: it's a stdio server and
waits for input indefinitely. Use `doctor` and the client's own listing instead.

## Step 8: report to the user

Finish with a short summary:

- the interpreter path the clients will launch (`$PY`),
- the tools installed and the clients configured,
- vendor paths stored, and any still missing,
- external requirements left for the user (licenses, ipopt/Gurobi, Julia, SLURM),
- that MCP clients load new servers only at startup: restart Claude Code or Codex
  (start a new session), and fully quit and reopen Claude Desktop,
- a first prompt to try, such as *"Create the IEEE 9-bus case in pandapower and run an
  AC power flow."*

## Troubleshooting

| Symptom | Fix |
|---|---|
| `zsh: no matches found: powermcp[...]` | Quote the requirement: `"powermcp[andes]"`. |
| `Not available on this platform/Python, skipped: <tool>` | That tool is Windows-only, or (for `surge`) needs Python 3.12+. Use another venv or skip the tool. |
| `No module named pip` | uv venv: install with `uv pip install --python "$PY" ...` and don't pass `--yes` to `powermcp install`. |
| A server shows as failed in the client | Check that the entry's `command` path exists, then run `"$PY" -m powermcp doctor <tool>`. |
| PSS/E or PowerFactory fails to import | The venv's Python version doesn't match the vendor folder (`PSSPY311` needs 3.11). Rebuild the venv with the matching Python. |
| Tool calls refuse a file path | The file is outside the allowed roots; see step 6. |
| Codex servers vanish on Windows | The Codex *Desktop* app has been reported to rewrite `~/.codex/config.toml`. Re-run step 5b after it does. The Codex CLI is unaffected. |

To upgrade later: `"$PY" -m pip install --upgrade "powermcp[<same extras>]"`, then
re-run step 5b with the full tool list.
