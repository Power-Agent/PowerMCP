"""FastMCP factory: register all domain tools."""

from mcp.server.mcpserver import MCPServer as FastMCP

from opendss_tools.configuration import register_configuration_tools
from opendss_tools.interactive_view import register_interactive_view_tools
from opendss_tools.model import register_model_tools
from opendss_tools.results import register_results_tools
from opendss_tools.simulation import register_simulation_tools


def create_mcp() -> FastMCP:
    mcp = FastMCP("PyDSS-MCP")
    register_configuration_tools(mcp)
    register_model_tools(mcp)
    register_simulation_tools(mcp)
    register_results_tools(mcp)
    register_interactive_view_tools(mcp)
    return mcp
