"""PowerMCP — MCP servers for power-system software.

A single distribution that bundles MCP servers for pandapower, PyPSA, ANDES,
Egret, surge, OpenDSS, HOPE, PSCAD, PSS/E, PSLF, PowerWorld, PowerFactory and
LTSpice. Install the core (`pip install powermcp` → pandapower + PyPSA) and add
tools via extras (`pip install powermcp[psse]`). Configure and wire up MCP
clients with the `powermcp` CLI (`powermcp install`).
"""

__version__ = "0.2.1"

__all__ = ["__version__"]
