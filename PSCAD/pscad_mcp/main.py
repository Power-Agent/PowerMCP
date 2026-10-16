import logging
import sys
import os
from mcp.server.mcpserver import MCPServer as FastMCP

# Add the PSCAD project directory to sys.path to allow package imports when run
# directly as a script.  The installed console entry point needs no adjustment.
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from pscad_mcp.tools.app_tools import register_app_tools
from pscad_mcp.tools.project_tools import register_project_tools
from pscad_mcp.tools.data_tools import register_data_tools
from pscad_mcp.tools.simset_tools import register_simset_tools

# Configure central logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pscad-mcp")

def create_server() -> FastMCP:
    """
    Factory to create and configure the FastMCP server.
    Applies modularity by registering tools from separate modules.
    """
    mcp = FastMCP("PSCAD-Modular")

    # Register tool groups (SRP)
    register_app_tools(mcp)
    register_project_tools(mcp)
    register_data_tools(mcp)
    register_simset_tools(mcp)
    
    logger.info("PSCAD MCP Server initialized with modular tools.")
    return mcp

def main():
    """Main entry point."""
    mcp = create_server()
    mcp.run()

if __name__ == "__main__":
    main()
