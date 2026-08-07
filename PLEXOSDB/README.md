# PLEXOSDB — PowerMCP connector

A thin re-export of [`plexosdb-mcp`](https://github.com/NatLabRockies/plexosdb/tree/main/src/plexosdb-mcp)'s
own MCP server (direct PLEXOS object/property/membership CRUD — 29 tools) plus two
tools PowerMCP adds, `translate_to_sienna` and `compare_solutions`, that call
[`r2x`](https://pypi.org/project/r2x/) directly.

No PLEXOS license, PLEXOS install, or vendor network call is required anywhere in
this connector: `plexosdb` reads and writes the PLEXOS XML database format directly
via a pure-Python/SQLite implementation. This is the PLEXOS-side half of a two-format
proposal — the paired `SIENNA` connector (solve + `translate_to_plexos`) is tracked
separately as [PowerMCP #54](https://github.com/Power-Agent/PowerMCP/issues/54); the
two share no PowerMCP code, only the upstream `r2x` dependency each calls directly.

## Install

Two packages are needed. Only one of them is on PyPI.

**1. PowerMCP with the `plexosdb` extra** (covers `r2x` — the translation library):

```bash
pip install "powermcp[plexosdb]"
```

**2. `plexosdb-mcp` itself, manually, from source.** It is a real, cleanly packaged
project (its own `pyproject.toml`, versioned, with a `plexosdb-mcp` console script),
just not yet released to PyPI. Its own metadata pins a direct git dependency on
`plexosdb`, and PyPI rejects packages that declare that — which is also why
PowerMCP's own `plexosdb` extra above does not (and cannot) pull it in automatically
without breaking `pip install powermcp` for everyone else:

```bash
pip install "plexosdb-mcp @ git+https://github.com/NatLabRockies/plexosdb.git@main#subdirectory=src/plexosdb-mcp"
```

Then run it through PowerMCP as usual:

```bash
powermcp run plexosdb
```

Verify both real installs and the resulting tool surface with `uv`:

```bash
uv pip install plexosdb r2x
uv pip install "plexosdb-mcp @ git+https://github.com/NatLabRockies/plexosdb.git@main#subdirectory=src/plexosdb-mcp"
python -c "from plexosdb_mcp.server import build_mcp_server; print(build_mcp_server())"
```

### Why `powermcp run plexosdb` launches this as a script, not a module

`PLEXOSDB/plexosdb_mcp/main.py` deliberately lives in a package also named
`plexosdb_mcp` — the same import name as the upstream distribution it re-exports
(mirroring `powerio/powerio_mcp.py`'s re-export of the `powerio` package). Because of
that shared name, the registry launches it as a **script** (`entry_rel=
"plexosdb_mcp/main.py"`), not as a module. Module-style launch would add `PLEXOSDB/`
itself to `sys.path`, and `import plexosdb_mcp` inside `main.py` would then resolve to
*this* package before ever reaching the real, installed one — confirmed by direct
testing while building this connector. Script launch only puts this file's own
directory on `sys.path`, so the bare `import plexosdb_mcp` correctly falls through to
site-packages. For the same reason, do not `pip install -e PLEXOSDB` into the same
environment you're also installing the upstream `plexosdb-mcp` package into and expect
both to cleanly coexist as independent site-packages entries.

## Usage: inspecting a PLEXOS study

Every re-exported plexosdb-mcp tool operates on an in-memory session, keyed by a
`session_id` returned from `open_xml_session`:

```python
from plexosdb_mcp.server import build_mcp_server, MCPServerState

state = MCPServerState()
server = build_mcp_server(state)  # or import plexosdb_mcp.main's `mcp` directly

session = state.open_xml_session("/path/to/Study.xml")
session_id = session["session_id"]

# then, via MCP or by calling the registered tool functions directly:
#   list_classes(session_id)
#   list_objects_by_class(session_id, "Generator")
#   get_object_properties(session_id, "Generator", "Coal_Gen")
#   list_object_memberships(session_id, "Generator", "Coal_Gen")
#   ... 25 more (session/discovery/edit/export) — see `capabilities` below.
```

Run `plexosdb-mcp capabilities` (installed by the git command above) for the full,
categorized tool list, or `plexosdb-mcp doctor` to check `fastmcp`/`plexosdb` are
importable and that an empty in-memory session opens cleanly.

## Usage: `translate_to_sienna`

```python
from plexosdb_mcp.main import translate_to_sienna

result = translate_to_sienna(
    xml_path="/path/to/Study.xml",
    model_name="Base",           # a PLEXOS Model object name — see list_models
    output_path="/tmp/out/system.json",
)
# {"ok": True, "output_path": ..., "model_name": "Base",
#  "component_types": {"ACBus": 12, "ThermalStandard": 4, ...}}
```

This calls r2x's real, public API directly — no PowerMCP-authored bridge module:

1. `r2x_plexos.PLEXOSParser` parses the PLEXOS XML into an `r2x_core.System`.
2. `r2x_plexos_to_sienna.plexos_to_sienna` translates that System to a Sienna-shaped
   System.
3. `r2x_sienna.SiennaExporter` writes it to `output_path` as **Sienna PSY JSON** —
   the format PowerSystems.jl consumes, and what the sibling `SIENNA` connector
   (PowerMCP #54) loads and solves.

`compare_solutions(xml_path_a, model_name_a, xml_path_b, model_name_b)` parses two
PLEXOS models the same way and diffs their component-type counts — useful for
comparing two scenarios of a study, or a study before/after an edit made through
plexosdb-mcp's own CRUD tools. It does not solve anything (no PLEXOS license is
present); solving is the paired `SIENNA` connector's job.

## Known upstream limitation (verified, not a PowerMCP defect)

`translate_to_sienna`/`compare_solutions` were exercised end-to-end against a real
PLEXOS XML study (`plexosdb`'s own test fixture, `tests/data/run_of_river_case/
TestSystem.xml` — a full, non-trivial study: 103 PLEXOS classes, multiple generators,
7 Models/scenarios) using the exact commands below. Session inspection (open the XML,
list classes, list objects by class, read object properties and memberships) worked
correctly end to end. The translation step currently does not, for a reason confirmed
to be upstream:

```bash
uv pip install plexosdb r2x
uv pip install "plexosdb-mcp @ git+https://github.com/NatLabRockies/plexosdb.git@main#subdirectory=src/plexosdb-mcp"
git clone --depth 1 https://github.com/NatLabRockies/plexosdb.git
python -c "
from r2x_core import PluginContext
from r2x_plexos import PLEXOSConfig, PLEXOSParser
cfg = PLEXOSConfig(fpath='plexosdb/tests/data/run_of_river_case/TestSystem.xml', model_name='Base')
PLEXOSParser.from_context(PluginContext(config=cfg)).run()
"
# r2x_core.exceptions.PluginError: PLEXOSParser build failed:
#   Attribute 'Chrono Date To' not found for class 'Horizon'.
```

`r2x_plexos` (PyPI `r2x_plexos==0.2.0`, pulled in transitively by `r2x==2.1.0`)
resolves a PLEXOS model's simulation horizon by reading its `Horizon` object's
"Chrono Date From"/"Chrono Date To" attributes
(`r2x_plexos.utils_plexosdb.resolve_horizon_for_model`), and only catches
`AssertionError` when they are unset. `plexosdb` (both the PyPI `1.5.0` release and
the `1.6.0` HEAD pulled in transitively by the git-installed `plexosdb-mcp`) instead
raises `plexosdb.exceptions.NotFoundError` in that case — not a subclass of
`AssertionError` — so the exception propagates instead of being treated as "horizon
not configured." This reproduces on **every** Model in the test fixture (none of its
7 Models set explicit Chrono dates), which is the common case for PLEXOS studies that
don't use the chronological/rolling-horizon feature — this is not a fixture-specific
edge case. `translate_to_sienna`/`compare_solutions` in this connector call
`r2x_plexos.PLEXOSParser` exactly as documented, so they hit the same error on studies
shaped like this one until upstream fixes the exception type mismatch (or a model with
explicit Chrono Date attributes is supplied).

## What's out of scope here

- Forking or vendoring `plexosdb`, `plexosdb-mcp`, or `r2x`.
- Requiring a PLEXOS license, install, or vendor network call anywhere in this
  connector.
- Publishing `plexosdb-mcp` to PyPI ourselves — that's upstream's call.
- Solving translated Sienna systems — that's the sibling `SIENNA` connector
  (PowerMCP #54), which also owns `translate_to_plexos`.
