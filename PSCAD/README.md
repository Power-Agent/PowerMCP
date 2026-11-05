# PSCAD Enterprise MCP Server

A professional, robust Model Context Protocol (MCP) server for **Power System Computer Aided Design (PSCAD)**. This server enables AI assistants (like Claude and Gemini) to automate PSCAD simulations, manage projects, and analyze results directly on a local Windows machine.

## 🚀 Key Features

- **Local-First Approach**: Optimized for local Windows automation using `mhi.pscad.application()`.
- **Source-Enriched Documentation**: Uses AST (Abstract Syntax Tree) analysis to extract decorators (like `@rmi` and `@requires`) and type hints directly from the `mhi-pscad` library, providing the AI with deep API awareness.
- **Execution Watchdog**: A 30-second timeout layer prevents AI tools from hanging if PSCAD is frozen or showing a modal dialog.
- **Process Monitoring**: OS-level detection of `PSCAD.exe` crashes or closures.
- **Thread-Safe Command Queue**: Ensures sequential execution, critical for PSCAD's single-threaded COM/RMI interface.

---

## 🛠 Installation

### 1. Prerequisites
- **Windows OS**: Required for local PSCAD automation (RMI).
- **PSCAD Installed**: Ensure PSCAD and its Python libraries are available on your system.
- **Python 3.11+**: Recommended for best compatibility.

### 2. Automated Setup
The easiest way to get started is by running the automated installer:

```bash
# Clone the repository
git clone https://github.com/LL0pez20/pscad-mcp.git
cd pscad-mcp

# Run the installer
python mcp_installer.py
```

The installer will:
- Install the `pscad-mcp` package and all dependencies.
- Synchronize your local PSCAD API documentation (Markdown + Raw).
- Generate the exact configuration commands for your AI tools.

---

## 🤖 AI Tool Integration

Once the server is installed, you can add it to your favorite AI assistant using the following commands:

### Gemini CLI
Connect the PSCAD MCP server to your Gemini CLI:
```bash
gemini mcp add pscad-mcp python pscad_mcp/main.py
```

### Claude Code
If you are using Anthropic's **Claude Code** (the agentic CLI), add it with:
```bash
claude mcp add pscad-mcp python pscad_mcp/main.py
```

### Claude Desktop
For the **Claude Desktop** app, add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pscad": {
      "command": "python",
      "args": ["/path/to/pscad-mcp/pscad_mcp/main.py"]
    }
  }
}
```
*Note: The `mcp_installer.py` will print the absolute path for you.*

---

## 🏗 Implementation Details

### Architecture (SOLID Principles)
The server is built using a modular package structure to ensure maintainability and testability:
- **`core/connection_manager.py`**: A **Singleton** that manages the lifecycle of the PSCAD instance and monitors OS-level process health.
- **`core/executor.py`**: Implements the **Command/Proxy Pattern**. All calls to PSCAD are proxied through a single-worker thread pool with an `asyncio` watchdog.
- **`tools/`**: Modularized toolsets (App, Project, Data, SimSet) following the **Single Responsibility Principle**.

### Safety Mechanisms
1. **JSON-RPC Compliance**: The server enforces strict JSON serializability of all return types and prevents `stdout` pollution.
2. **Heartbeat Checks**: Before every command, the server performs a "heartbeat" check (`is_busy()`) to ensure the connection is still valid.
3. **Parameter Validation**: The `validate_component_parameters` tool uses the library's internal `range()` metadata to verify values before execution.

---

## 📖 Available Tools

### System & Lifecycle
- `get_local_pscad`: Attach to/Launch a local PSCAD instance.
- `get_pscad_status`: Health check and version info.
- `sync_documentation`: Extract and update AI's internal reference files (20 modules covered).
- `list_documentation`: List available PSCAD API documentation modules.
- `read_documentation`: Read clean, LLM-optimized Markdown documentation for a specific module.
- `repair_connection`: Force-reset the RMI connection.
- `quit_pscad`: Terminate the PSCAD application.

### Project & Components
- `load_projects`: Load `.pscx`, `.pslx`, or `.pswx` files.
- `list_projects`: Get a list of loaded cases/libraries.
- `run_project`: Start a simulation (includes license verification).
- `get_run_status`: Monitor simulation progress.
- `find_components`: Locate components by name or definition.
- `get_component_parameters`: Retrieve all parameter values for a component.
- `set_component_parameters`: Update multiple parameters at once.
- `validate_component_parameters`: Check if values are within the legal range before setting.
- `get_project_settings`: Retrieve project runtime settings.
- `set_project_settings`: Update project runtime settings (Duration, TimeStep, etc.).

### Simulation Sets (Batch)
- `list_simulation_sets`: Discover defined batch runs in a project.
- `run_simulation_set`: Execute a collection of project tasks.
- `add_task_to_set`: Programmatically add project tasks to a simulation set.

### Data & Results
- `get_project_output`: Capture simulation runtime messages.
- `read_output_file`: Parse `.psout` or `.out` results into JSON.

---

## 🧪 Testing & Validation
Run the full test suite to verify logic, protocol integrity, and tool behavior:
```bash
# Run all tests
python -m unittest discover tests

# Run enhanced tool tests specifically
python -m unittest tests/test_enhanced_tools.py
```
*Note: Unit tests use mocks to simulate PSCAD behavior, allowing verification on any OS.*
