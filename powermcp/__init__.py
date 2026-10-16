"""PowerMCP: MCP servers for power-system software.

A single distribution that bundles MCP servers for pandapower, PyPSA, ANDES,
Egret, surge, OpenDSS, HOPE, PSCAD, PSS/E, PSLF, PowerWorld, PowerFactory and
LTSpice. Install the core (`pip install powermcp`, which brings pandapower,
PyPSA and PowerIO) and add tools via extras (`pip install powermcp[psse]`).
Configure and connect MCP clients with the `powermcp` CLI (`powermcp install`).
"""

__version__ = "0.4.0"

__all__ = ["__version__"]
