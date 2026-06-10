# `powermcp` — package & CLI

This folder is the **PowerMCP core package**: the CLI installer (`powermcp install`),
the launcher (`powermcp run`), the central config (`~/.powermcp/config.toml`), the tool
registry, and the MCP client-config writers. The actual MCP servers live in the
top-level tool dirs (`PSSE/`, `pandapower/`, …) and are shipped into the wheel under
`powermcp/_servers/` at build time.

This guide shows how to **install** and **test** the packaged version.

---

## 1. Install (as a user)

Requires **Python 3.10+**.

```bash
pip install powermcp
```

The base install includes only the two zero-setup open-source engines: **pandapower**
and **PyPSA**. Everything else is opt-in via an extra:

```bash
pip install "powermcp[psse]"            # one tool
pip install "powermcp[andes,opendss]"   # several
pip install "powermcp[opensource]"      # all open-source tools
pip install "powermcp[all]"             # everything
```

> On Windows use the `py` launcher if `python` isn't on PATH:
> `py -m pip install powermcp`. Quote the brackets in PowerShell/zsh: `"powermcp[psse]"`.

### Available extras

| Extra | Tool(s) | Notes |
|---|---|---|
| *(none / core)* | pandapower, PyPSA | always installed |
| `andes` | ANDES | |
| `egret` | Egret | + needs an external solver (ipopt/Gurobi) |
| `opendss` | OpenDSS | |
| `surge` | surge | **Python 3.12–3.14 only** |
| `hope` | HOPE | + needs Julia at runtime |
| `ltspice` | LTSpice | executable **auto-detected** (override with `ltspice.exe`) |
| `powerworld` | PowerWorld | needs licensed Simulator (COM); extra also installs `numba` (required by esa 1.3.5) |
| `psse`, `pslf`, `powerfactory` | PSS/E, PSLF, PowerFactory | engine loaded from a configured local path |
| `pscad-windows` | PSCAD | Windows only; pulls `mhi-pscad`/`mhi-psout` |
| `opensource` | all open-source tools | convenience group |
| `windows` / `all` | Windows / everything | convenience groups |

---

## 2. Set it up

```bash
powermcp install
```

The interactive wizard:
1. lets you pick tools (pandapower + PyPSA pre-checked; Windows-only tools hidden off Windows),
2. prompts for the local software path of any closed-source tool you select,
3. `pip install`s the chosen extras,
4. writes the MCP client config for **Claude Desktop**, **Claude Code**, and the **Codex CLI**.

> In the interactive picker you must press **SPACE to toggle each tool**, then ENTER to
> confirm — pressing ENTER alone keeps only the preselected core tools. If your terminal
> doesn't render the checkbox well, use `--tools`/`--all` below instead.

**Choose tools non-interactively** (recommended when scripting or if the picker misbehaves):

```bash
powermcp install --tools psse,andes              # core + the listed tools
powermcp install --all                           # every tool available on this platform
powermcp install --tools psse --clients claude-desktop
```

`--tools` takes comma-separated tool ids (see `powermcp list`); core tools are always
included, and ids not valid on your platform/Python are skipped with a notice.

**Re-running is non-destructive.** The picker pre-checks the tools you've already installed
or configured (and any already present in the targeted client config), so confirming
**preserves and updates** your existing setup instead of resetting to core. Paths such as
LTSpice's are auto-detected and pre-filled, so you can usually just press Enter.

Useful flags: `--dry-run` (preview, write nothing — not even `config.toml`),
`--yes` (non-interactive core only), `--tools <ids>` / `--all` (pick tools without the
picker), `--clients claude-desktop,codex` (choose which clients; `none` to skip).

### All CLI commands

```bash
powermcp install                         # setup wizard
powermcp run <tool>                      # launch a server over stdio (used by clients)
powermcp list                            # list tools, extras, windows-only flags
powermcp doctor                          # check deps + configured paths for every tool
powermcp config show                     # print ~/.powermcp/config.toml
powermcp config set <tool>.<key> <path>  # set one path
powermcp --version
```

### Closed-source tool paths

These are stored in `~/.powermcp/config.toml` (captured by the wizard, or set manually):

```bash
powermcp config set psse.python_lib "C:\Program Files\PTI\PSSE36\36.2\PSSPY311"
powermcp config set psse.bin        "C:\Program Files\PTI\PSSE36\36.2\PSSBIN"
powermcp config set ltspice.exe     "C:\Program Files\ADI\LTspice\LTspice.exe"
powermcp config set pslf.python_lib "C:\Program Files\GE PSLF\PSLF_PYTHON"
powermcp config set powerfactory.python_path "...\DIgSILENT\PowerFactory 2024\Python\3.11"
powermcp config set hope.repo_root  "C:\src\HOPE"
```

Resolution order for each key is **environment variable** (`POWERMCP_PSSE_BIN`, …) →
**config.toml** → **legacy default** → a clear "run `powermcp install`" error.

> **LTSpice is auto-detected** in standard install locations (modern ADI, legacy LTC, Wine),
> so `ltspice.exe` usually doesn't need to be set at all — the server resolver falls back to
> detection (env/config → auto-detect → legacy), and the wizard pre-fills the detected path.
> Set it only for a non-standard install.

### Use PowerMCP in Claude Desktop

Claude Desktop has no CLI — it reads a JSON config file. Let the installer write/merge it:

```bash
powermcp install --clients claude-desktop
```

This merges one server per selected tool into `claude_desktop_config.json`, preserving any
servers you already have (and backing the file up once). The file lives at:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Preview without writing anything: `powermcp install --clients claude-desktop --dry-run`.

**Manual setup** — open that file (in Claude Desktop: **Settings → Developer → Edit Config**)
and add entries under `mcpServers`. Use the **absolute interpreter path**: Claude Desktop is a
GUI app and does *not* inherit your shell PATH, so a bare `python`/`powermcp` usually won't be
found.

```json
{
  "mcpServers": {
    "powermcp_pandapower": {
      "command": "D:\\PowerMCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "powermcp", "run", "pandapower"]
    },
    "powermcp_psse": {
      "command": "D:\\PowerMCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "powermcp", "run", "psse"]
    }
  }
}
```

(JSON needs escaped backslashes on Windows. Find the interpreter with
`python -c "import sys; print(sys.executable)"`.)

**Apply & verify:** fully **quit and reopen** Claude Desktop — closing the window isn't enough;
exit it from the system tray / menu bar, then relaunch. The PowerMCP tools then appear under the
tools (🔨) control in the message box, and **Settings → Developer** lists each server with its
connection status.

**Closed-source tools:** set the path first (`powermcp config set …`), confirm with
`powermcp doctor`, then restart Claude Desktop.

### Use PowerMCP in Claude Code

**Option A — let the installer do it (recommended):**

```bash
powermcp install --clients claude-code
```

This adds one MCP server per selected tool to the **user scope** of Claude Code
(the `mcpServers` block of `~/.claude.json`), so they're available in every project.
Each entry uses the absolute interpreter path (`<python> -m powermcp run <tool>`) so
Claude Code can always launch it. Re-running is idempotent and prunes tools you deselect.

**Option B — add them manually with the Claude Code CLI:**

```bash
# --scope user = available everywhere; the `--` separates Claude's flags from the command
claude mcp add powermcp_pandapower --scope user -- python -m powermcp run pandapower
claude mcp add powermcp_psse       --scope user -- python -m powermcp run psse
```

If `python` on PATH isn't the interpreter that has `powermcp` installed (e.g. you
installed into a venv), use the **full interpreter path** so it always resolves:

```bash
# Windows (venv) example
claude mcp add powermcp_pandapower --scope user -- "D:\PowerMCP\.venv\Scripts\python.exe" -m powermcp run pandapower
```

**Verify and use:**

```bash
claude mcp list                     # should list the powermcp_* servers (✓ connected)
claude mcp get powermcp_pandapower  # show one server's details
```

Inside a Claude Code session, run `/mcp` to see connected servers and their tools, then
just ask — e.g. *"create an empty pandapower network and run a power flow."*

**Scopes:** `--scope user` (you, everywhere — what the installer uses) ·
`--scope project` (shared via a checked-in `.mcp.json`, prompts teammates for approval) ·
`--scope local` (this project only, private to you).

**Closed-source tools:** set the software path first (e.g.
`powermcp config set psse.python_lib "…\PSSPY311"`) and confirm with `powermcp doctor`
before adding the server, otherwise the tool will report an actionable error on first call.

**To remove a server:** `claude mcp remove powermcp_pandapower --scope user`.

---

## 3. Run from a clone (no install)

Every server is still a standalone script, so you can clone the repo and run one directly
for Claude Desktop without `pip install`:

```bash
python pandapower/panda_mcp.py
python PSSE/psse_mcp.py     # uses ~/.powermcp/config.toml if present, else legacy paths
```

---

## 4. Test the package (developers)

The test suite lives in [`../tests`](../tests) (≈62 tests). It needs no licensed software —
vendor engines are stubbed, and server launches are checked with the stdio loop monkeypatched.

### A. Quick loop — editable install

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows;  source .venv/bin/activate elsewhere
pip install -e . pytest
pytest -q
```

`pip install -e .` picks up source edits live, so re-run `pytest` after each change.

### B. Full gate — build the wheel and test the installed artifact

This is what CI should run: it proves the wheel ships correctly and resolves paths in the
**installed (wheel) layout**, which differs from the editable/checkout layout.

```bash
# 1) build
python -m venv build-env && build-env\Scripts\python -m pip install build
build-env\Scripts\python -m build           # writes dist/powermcp-*.whl (+ sdist)

# 2) install the wheel into a clean venv
python -m venv test-env
test-env\Scripts\python -m pip install dist\powermcp-0.1.0-py3-none-any.whl pytest

# 3) run the suite against the INSTALLED package (run from a dir without the repo on the path)
copy ..\tests to a temp dir, then:  test-env\Scripts\python -m pytest <tempdir>\tests -q
```

What the build gate confirms:
- `pip install powermcp` pulls **core only** (no esa/andes/surge/psspy):
  `test-env\Scripts\python -m pip list`
- the data files ship (2184 PSS/E JSONs, OpenDSS `13Bus/IEEELineCodes.DSS`, surge schema):
  inspect the wheel with `python -m zipfile -l dist\powermcp-*.whl`

### C. Manual smoke checks

```bash
powermcp --version
powermcp list
powermcp doctor                                  # status table for all tools
powermcp install --yes --dry-run                 # preview client config, write nothing
powermcp config set ltspice.exe C:\tmp\x.exe && powermcp config show
powermcp run pandapower                          # starts a stdio server; Ctrl-C to stop
```

`powermcp doctor` is the fastest health check: green = the Python package is importable;
yellow = a path/config is missing; it also reminds you which tools need external solvers
(HiGHS, ipopt, Gurobi) or Julia at runtime.

### What the tests cover (mapped to the suite)

| File | Focus |
|---|---|
| `test_config.py` | config read/write, `get_path` resolution + actionable errors, Windows-path round-trip |
| `test_registry.py` | tool metadata consistency, path resolution across layouts |
| `test_runner.py` | `powermcp run` launches once; no library shadowing; preflight + namespace-package probe; `python -m powermcp` |
| `test_vendor_import.py` | PSS/E & PSLF import **without** the software and init the engine exactly once |
| `test_clients.py` | idempotent merge, foreign-server preservation, prune, backup, Codex TOML |
| `test_wizard.py` | tool selection (`--tools`/`--all`, preselection of installed/configured tools), Windows/surge filtering, non-interactive handling |
| `test_doctor.py` | dependency/path status, namespace-shadow guard |
| `test_detect.py` | LTSpice executable auto-detection across install layouts |

> **Licensed tools (PSS/E, PSLF, PowerFactory, PSCAD, PowerWorld, LTSpice)** can't run in CI.
> The suite verifies they *import safely* and produce actionable errors; running an actual
> tool requires the software installed and a `powermcp config set …` path, then
> `powermcp doctor` and a live `powermcp run <tool>` from your MCP client.

---

## 5. Layout

```
powermcp/
  cli.py          # `powermcp` entry point (install/run/list/config/doctor)
  wizard.py       # interactive installer
  runner.py       # launches a server by tool id
  registry.py     # the tool registry (single source of truth)
  config.py       # ~/.powermcp/config.toml  + get_path()
  paths.py        # ~/.powermcp/runs/<tool> writable dirs
  doctor.py       # health checks
  clients/        # claude_desktop / claude_code / codex config writers
  _servers/       # (wheel only) the tool dirs, shipped verbatim at build time
```
