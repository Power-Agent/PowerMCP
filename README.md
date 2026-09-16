# PowerMCP ⚡

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%20to%203.14-blue.svg)](https://www.python.org/downloads/)

PowerMCP is an open-source collection of MCP servers for power system software like PowerWorld and OpenDSS. These tools enable LLMs to directly interact with power system applications, facilitating intelligent coordination, simulation, and control in the energy domain.

## 🌟 What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/introduction) (MCP) is a revolutionary standard that enables AI applications to seamlessly connect with various external tools. Think of MCP as a universal adapter for AI applications, similar to what USB-C is for physical devices. It provides:

- Standardized connections to power system software and data sources
- Secure and efficient data exchange between AI agents and power systems
- Reusable components for building intelligent power system applications
- Interoperability between different AI models and power system tools

## 🤝 Our Community Vision

We're building an open-source community focused on accelerating AI adoption in the power domain through MCP. Our goals are:

- **Collaboration**: Bring together power system experts, AI researchers, and software developers
- **Innovation**: Create and share MCP servers for various power system software and tools
- **Education**: Provide resources and examples for implementing AI in power systems
- **Standardization**: Develop best practices for AI integration in the energy sector

## 🚀 Getting Started with MCP

### 📖 Quick start

> **🚀 New to PowerMCP? Start here!**

The recommended way to get started is the `powermcp` package and its installer (see the **Installation** section below):

```bash
pip install powermcp
powermcp install        # pick tools, capture local paths, write your MCP client config
```

> 📋 The **[PowerMCP Tutorial PDF](https://github.com/Power-Agent/PowerMCP/blob/main/PowerMCP_Tutorial.pdf)** documents the original **low-code / manual** setup — cloning the repo and hand-editing the Claude Desktop config. It predates the `powermcp` installer and is **not the recommended path**; use it only if you specifically want the manual approach.


### Video Demos

Check out these demos showcasing PowerMCP in action:

- [**Contingency Evaluation Demo**](https://www.youtube.com/watch?v=MbF-SlBI4Ws): An LLM automatically operates power system software, such as PowerWorld and pandapower, to perform contingency analysis and generate professional reports.

- [**Loadgrowth Evaluation Demo**](https://www.youtube.com/watch?v=euFUvhhV5dM): An LLM automatically operates power system software, such as PowerWorld, to evaluate different load growth scenarios and generate professional reports with recommendations.

### Useful MCP Tutorials

MCP follows a client-server architecture where:

* **Hosts** are LLM applications (like Claude Desktop or IDEs) that initiate connections
* **Clients** maintain 1:1 connections with servers, inside the host application
* **Servers** provide context, tools, and prompts to clients

Check out these helpful tutorials to get started with MCP:

- [**Getting Started with MCP**](https://modelcontextprotocol.io/introduction): Official introduction to the Model Context Protocol fundamentals.
- [**Core Architecture**](https://modelcontextprotocol.io/docs/concepts/architecture): Detailed explanation of MCP's client-server architecture.
- [**Building Your First MCP Server**](https://modelcontextprotocol.io/docs/develop/build-server): Step-by-step guide to creating a basic MCP server.
- [**Anthropic MCP Tutorial**](https://docs.claude.com/en/docs/mcp): Learn how to use MCP with Claude models.
- [**Cursor MCP Tutorial**](https://cursor.com/docs/context/mcp): Learn how to use MCP with Cursor.
- [**Other Protocol**](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf): Open AI Function Calling Tool

## 📦 Installation

PowerMCP installs as a single Python package with an interactive CLI. Python 3.10 through 3.14 is supported.

```bash
pip install powermcp
```

The base install includes the open-source engines that need no extra setup — **pandapower**, **PyPSA**, and **PowerIO** (the cross-server case-conversion substrate). Every other tool is opt-in via an extra:

```bash
pip install powermcp[psse]              # add PSS/E support
pip install powermcp[andes,opendss]     # add several tools at once
pip install powermcp[opensource]        # all open-source tools (ANDES, Egret, OpenDSS, surge, HOPE, LTSpice, GenX)
pip install powermcp[all]               # everything (closed-source tools still need the local software)
```

### Set up with the interactive installer

```bash
powermcp install
```

The wizard lets you pick tools (pandapower + PyPSA + PowerIO pre-selected), captures the local install path for any closed-source/EXE-based tools you choose (PSS/E, PSLF, PowerFactory, PSCAD, LTSpice), installs the right extras, and writes the MCP client configuration for **Claude Desktop**, **Claude Code**, and the **Codex CLI**. Use `--dry-run` to preview the changes, or `--yes` for a non-interactive core install.

In the interactive picker, move with ↑/↓ and **press SPACE to toggle each tool** before ENTER (ENTER alone keeps only the preselected tools). Prefer not to use the checkbox? Choose tools directly:

```bash
powermcp install --tools psse,andes      # core + the listed tools
powermcp install --all                   # every tool available on this platform
```

Re-running `powermcp install` pre-checks the tools you've already installed or configured, so it **preserves and updates** your setup instead of resetting to the core tools. Paths for tools like LTSpice are **auto-detected and pre-filled**, so you can usually just press Enter.

### CLI commands

| Command | Description |
|---|---|
| `powermcp install` | Setup wizard — interactive, or `--tools <ids>` / `--all` (also `--dry-run`, `--yes`, `--clients`) |
| `powermcp run <tool>` | Launch a server over stdio (used by the generated client config) |
| `powermcp list` | List the available tools, extras, and Windows-only flags |
| `powermcp doctor` | Check each tool's dependencies and configured paths |
| `powermcp config show` / `config set <tool>.<key> <path>` | Inspect / set local software paths |

### Closed-source / EXE-based tools

These tools wrap commercial or locally-installed software, so PowerMCP stores the local path in `~/.powermcp/config.toml` (captured by `powermcp install`, or set manually with `powermcp config set`):

| Tool | Config keys | Example |
|---|---|---|
| PSS/E | `psse.python_lib`, `psse.bin` | `powermcp config set psse.python_lib "C:\Program Files\PTI\PSSE36\36.2\PSSPY311"` |
| PSLF | `pslf.python_lib` | `powermcp config set pslf.python_lib "C:\Program Files\GE PSLF\PSLF_PYTHON"` |
| PowerFactory | `powerfactory.python_path` | `powermcp config set powerfactory.python_path "...\DIgSILENT\PowerFactory 2024\Python\3.11"` |
| LTSpice | `ltspice.exe` *(auto-detected)* | Found automatically in standard locations — usually no setup needed. Override: `powermcp config set ltspice.exe "C:\Program Files\ADI\LTspice\LTspice.exe"` |
| HOPE | `hope.repo_root`, `hope.julia_bin` | `powermcp config set hope.repo_root "C:\src\HOPE"` |
| GenX | `genx.repo_root` | `powermcp config set genx.repo_root "/home/me/GenX.jl"` — the GenX.jl checkout; `GENX_DIR` overrides it |
| PowerWorld | *(none)* | `esa` auto-discovers a running, licensed Simulator via COM; the `powerworld` extra also installs `numba` (required by esa) |
| PSCAD | *(none)* | `pip install powermcp[pscad-windows]` provides `mhi-pscad`; PSCAD must be installed |

> The Codex *Desktop* app on Windows has been reported to overwrite `~/.codex/config.toml`; the Codex *CLI* is unaffected. If you use both, re-run `powermcp install` after Desktop edits.

### Case compilation between servers (PowerIO)

PowerIO IR is the exchange format of this repository. PowerMCP runs the
server shipped in PowerIO 0.11.2 (`powermcp run powerio` is `python -m
powerio.mcp`); that server parses every grid exchange format, emits every
target, summarizes, diagnoses, normalizes, lowers multiconductor networks, and
calculates matrices. Its `parse` tool returns serialized **PowerIO IR
generation 2** (`"schema": "pio-ir"`, `"version": 2`), a typed module carrying
the electrical value, its provenance and its diagnostics. Every other server
here consumes that document: the pandapower, PyPSA, ANDES and Egret adapters
turn it into their own model with PowerIO's writers, and the Tellegen server
hands it to the native solver. PowerMCP itself never re-parses, re-validates,
or recomputes what PowerIO states; it routes a declared value to a consumer
that accepts it and owns only the final step into one simulator.

```python
parsed = parse(path="case9.raw")                     # powerio server
ir = parsed["powerio_ir"]
summarize(powerio_ir=ir)
calc_matrix(matrix="ptdf", powerio_ir=ir)            # rows and columns carry bus ids and branch identities
diagnostics(powerio_ir=ir)
import_case_from_json(powerio_ir=ir, output_path="case9.nc")  # PyPSA
load_network_from_json(powerio_ir=ir)                         # pandapower
load_model_from_json(powerio_ir=ir)                           # Egret
load_network_from_json(powerio_ir=ir, out_path="case9.m")     # ANDES
solve(powerio_ir=ir, formulation="dcopf")                     # tellegen
emit(format="psse", destination="case9.raw", powerio_ir=ir)
```

`powerio_ir` is the argument every adapter takes; `network_json` remains an
alias for the same document. A `ScenarioSet` requires `scenario_id`; a
`TimeSeries` requires `time_index`; nested collections require both. An
operating point entry reaches the solver as the network it states. The
`operating_point` argument remains an alias for `time_index`.

```python
import_case_from_json(
    powerio_ir=ir, output_path="dispatch.nc",
    scenario_id="high-demand", time_index=3,
)
```

Every adapter response carries the same tail: `value_type` (the PowerIO
structural type that was selected), `selection`, `diagnostics` (full PowerIO
records with code, severity, target, spans and suggested action) and
`warnings`. The powerio adapters add the emission `fidelity`
(`exact_same_format` when PowerIO echoed retained source bytes, `canonical` for
fresh output) and the typed `edits` report described below, because they own
the conversion into their own model. The `package` key keeps the IR context
earlier clients read.

The Tellegen tools carry the same four keys for the module they hand to the
native solver, and `solve_module` and `plan` add what the returned module
states. They take no typed `edits` list: Tellegen's own `edits` argument is the
native request object (`{"deltas": ..., "rates": ...}`) the CLI applies inside
the solve.

#### Typed edits before a solver import

The powerio adapters accept `edits`, a JSON list of what-if changes PowerIO
applies as typed updates before the conversion. The whole list is validated
first, then applied in list order; consecutive updates of one class apply as
one atomic batch, and a bus load reallocation sees the values produced by the
edits before it. The response reports the changed components, in application
order, under `edits`.

| op | keys |
|---|---|
| `set_load_active_power` | `load`, `mw`, `terminal?` |
| `set_load_reactive_power` | `load`, `mvar`, `terminal?` |
| `set_generator_active_power` | `generator`, `mw`, `terminal?` |
| `set_generator_reactive_power` | `generator`, `mvar`, `terminal?` |
| `set_generator_voltage_magnitude` | `generator`, `vm_pu` |
| `set_generator_in_service` | `generator`, `in_service` |
| `set_branch_in_service` | `branch`, `in_service` |
| `set_transformer_tap_ratio` | `transformer`, `tap_ratio` |
| `set_transformer_phase_shift` | `transformer`, `shift_degrees` |
| `set_switch_closed` | `switch`, `closed` |
| `set_branch_thermal_rating` | `branch`, `mva`, `terminal?` |
| `set_bus_load_active_power` | `bus`, `mw`, `allocation` (`proportional_to_current_active_power` or `equal`) |

Component ids are the stable identities PowerIO reports (`loads:0`,
`branches:3`, or the source uid). A bus demand edit names an allocation rule
because PowerIO never assigns aggregate demand to an arbitrary load.

```python
load_network_from_json(
    powerio_ir=ir,
    edits='[{"op": "set_load_active_power", "load": "loads:0", "mw": 91.5},'
          ' {"op": "set_branch_in_service", "branch": "branches:3", "in_service": false}]',
)
```

#### Distribution networks

A multiconductor value is rejected by a balanced solver until the caller asks
for the transformation: pass `to_balanced=True` (and `base_mva`) and the
response carries PowerIO's readiness report under `lowering`, or call the
powerio server's `to_balanced_report` and `to_balanced` tools first. Retaining
a component does not establish that the selected solver models it. Use `emit`
for a backend that needs files: OpenDSS output is a directory bundle whose
master DSS artifact `compile_opendss_file` accepts; `bmopf-json@0.1.0` and
`bmopf-json@0.2.0` select the BMOPF schema version (the latter writes draft
BMOPF 0.2, subject to Task Force approval); `geo-json` writes a geographic
layer.

The retired `Package`, `model-json`, `package_json` and package `study_commit`
formats require migration: re-parse the original case and pass its
`powerio_ir`. Study goals, branching and decisions belong to Tellegen.

PowerIO MCP paths support local files and `file://` URIs. Set
`POWERIO_MCP_ALLOWED_ROOTS` to an `os.pathsep` separated directory list to
constrain the shared path policy. With no root variable set, paths stay beneath
the directory the server process started in, which is rarely the directory an
operator means. Legacy single-root environment aliases remain supported.
Directory inputs check every descendant, and generated directories install from
private sibling staging paths. Place `POWERMCP_HOME` under an allowed root for
solver run artifacts. These checks cannot prevent another process from
replacing a path after validation.

### Tellegen (native solver and Studies)

[Tellegen](https://github.com/eigenergy/tellegen) solves DC power flow, DC OPF
with prices and dispatch, AC power flow and the SOCWR relaxation, computes
sensitivities, runs bounded capacity planning, and keeps durable Studies. It
consumes and produces PowerIO IR, so `powermcp run tellegen` is the third
consumer of the same format: the powerio server parses, Tellegen solves, and
the solution comes back as a `powerio.DcOpfSolution` module every other tool
can read.

Build the CLI and point PowerMCP at it:

```sh
cargo build -p tellegen-cli --features conic     # in a tellegen checkout
powermcp config set tellegen.binary /path/to/target/debug/tellegen
# or: export POWERMCP_TELLEGEN_BINARY=/path/to/tellegen, or put tellegen on PATH
powermcp doctor                                  # runs `tellegen capabilities`
```

Tools: `capabilities`, `contract`, `solve(powerio_ir | path, formulation,
edits, sensitivities, max_elements)`, `solve_module(..., out_path)`,
`plan(spec, ...)`, and the Study family `study_contract`, `study_create`
(`input_path` lets PowerIO parse a grid exchange file into the Study input),
`study_inspect`, `study_run`, `study_export`, `study_import`. A grid exchange
`path` is parsed by PowerIO in the server process and serialized to IR before
it reaches the binary; collection entries take `time_index` and `scenario_id`.
Tellegen takes a balanced network or a calculation instance and lowers nothing:
a multiconductor value is refused here, before the binary runs, so lower it
with the powerio server's `to_balanced` first. A module PowerIO marks with an
error is refused on the same terms as every other adapter refuses it.
Applying a Study proposal binds a recommendation to the Study and is a human
action: it is not a tool, and `study_run` refuses the `apply` operation.

The adapter accepts `POWERMCP_TELLEGEN_TIMEOUT_SECONDS` (default 1800) and
`POWERMCP_TELLEGEN_CANCEL_GRACE_SECONDS` (default 300). Equivalent keys live
under `[tellegen]` in the configuration file. Cancellation requests SIGTERM on
POSIX and CTRL_BREAK on a Windows process group, allowing the current exact
trial to finish and completed evidence to be saved. After the grace period, or
without a usable Windows console, a forced stop can retain only the previous
saved revision. Inspect the Study before retrying. See
[powermcp/TELLEGEN.md](powermcp/TELLEGEN.md).

### Running from a clone (without installing)

Every bundled server is still a standalone script. Clone the repo and run any server directly for use in Claude Desktop:

```bash
python pandapower/panda_mcp.py
python PSSE/psse_mcp.py          # uses ~/.powermcp/config.toml if present, else legacy default paths
python -m powerio.mcp            # powerio ships its own server; the clone holds no copy
```

### Testing with your LLMs

> **Note:** All MCPs should be tested via an MCP client (Claude Desktop, Claude Code, or Codex) before submitting a PR to ensure consistency.

`powermcp install` writes the client configuration for you. The generated entries look like the example in [`config.json`](config.json). (The **[PowerMCP Tutorial PDF](PowerMCP_Tutorial.pdf)** covers the older manual / low-code setup and isn't needed for the package install.)

## 📚 Documentation

For detailed documentation about MCP, please visit:
- [Model Context Protocol documentation](https://modelcontextprotocol.io/introduction)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Other General MCP Servers](https://smithery.ai/)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://power-agent.github.io/) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

### Core Team
- [Qian Zhang](https://www.linkedin.com/in/qian-zhang-75323111b/), [Steven Black](https://www.linkedin.com/in/steven-black-09322b31/), [Paulo Radatz](https://www.linkedin.com/in/pauloradatz/), [Andrea Pomarico](https://www.linkedin.com/in/andrea-pomarico-2695a2218/), [Muhy Eddin Za’ter](https://scholar.google.com/citations?user=_IFFYFAAAAAJ&hl=en), [Luan Lopes dos Santos](https://www.linkedin.com/in/luan-lopes/), [Stephen Jenkins](https://www.linkedin.com/in/stephenjenkins2/), [Maanas Goel](https://www.linkedin.com/in/maanas-goel/), [Shen Wang](https://www.linkedin.com/in/swang16/), [Drew Gray](https://www.linkedin.com/in/drew-gray-b09ba426/), [Samuel Talkington](https://samueltalkington.com/)

### Special Thanks
- All contributors who help make this project better
- [The Power and AI Initiative (PAI) at Harvard SEAS](https://pai.seas.harvard.edu/)
