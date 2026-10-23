from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer as FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor

async def list_simulation_sets(project_name: str) -> List[str]:
    """List all simulation sets defined in the current workspace.

    ``project_name`` is retained for backward-compatible MCP arguments.
    Simulation sets belong to the PSCAD workspace, not to one Project.
    """
    del project_name  # Kept only for MCP schema compatibility.
    pscad = pscad_manager.pscad
    return await robust_executor.run_safe(pscad.simulation_sets)


async def run_simulation_set(
    project_name: str,
    sim_set_name: str,
) -> str:
    """Run a simulation set and wait for all of its tasks to finish."""
    pscad = pscad_manager.pscad
    sim_set = await robust_executor.run_safe(
        pscad.simulation_set,
        sim_set_name,
    )

    # A simulation set may run much longer than the default 30-second
    # watchdog, so disable the watchdog for this blocking API call.
    await robust_executor.run_safe(sim_set.run, _timeout=0)

    return (
        f"Simulation set '{sim_set_name}' in project "
        f"'{project_name}' completed."
    )


async def add_task_to_set(
    project_name: str,
    sim_set_name: str,
    task_project_name: str,
) -> str:
    """Add a loaded project as a task in an existing simulation set."""
    del project_name  # Kept only for MCP schema compatibility.
    pscad = pscad_manager.pscad
    sim_set = await robust_executor.run_safe(
        pscad.simulation_set,
        sim_set_name,
    )
    await robust_executor.run_safe(
        sim_set.add_tasks,
        task_project_name,
    )
    return f"Task '{task_project_name}' added to set '{sim_set_name}'."

def register_simset_tools(mcp: FastMCP):
    """Register tools for batch simulation management."""
    mcp.tool()(list_simulation_sets)
    mcp.tool()(run_simulation_set)
    mcp.tool()(add_task_to_set)
