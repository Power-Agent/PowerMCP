from typing import Dict, Any
import os
import logging
from mcp.server.fastmcp import FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor

async def get_project_output(project_name: str) -> str:
    """Get the text output messages from the PSCAD project's runtime."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    return await robust_executor.run_safe(project.output)

async def read_output_file(file_path: str) -> Dict[str, Any]:
    """Read results from a .psout or .out file using mhi.psout."""
    try:
        import mhi.psout
    except ImportError:
        return {"error": "mhi-psout package not installed."}

    try:
        abs_path = os.path.abspath(file_path)
        with mhi.psout.open(abs_path) as psout:
            data = {}
            for channel in psout.channels():
                data[channel.name] = psout.channel(channel.name).values().tolist()
            return {"channels": list(data.keys()), "data": data}
    except Exception as e:
        return {"error": str(e)}

def register_data_tools(mcp: FastMCP):
    """Register tools for reading simulation results and output."""
    mcp.tool()(get_project_output)
    mcp.tool()(read_output_file)
