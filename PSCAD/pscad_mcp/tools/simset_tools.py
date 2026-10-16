from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer as FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor

async def list_simulation_sets(project_name: str) -> List[str]:
    """List all simulation sets defined in a project."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    # The documentation shows simulation_sets() returns a list of objects
    sim_sets = await robust_executor.run_safe(project.simulation_sets)
    return [ss.name for ss in sim_sets]

async def run_simulation_set(project_name: str, sim_set_name: str) -> str:
    """Run a specific simulation set (batch of tasks)."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    # Use the simulation_set(name) method we found in enriched docs
    sim_set = await robust_executor.run_safe(project.simulation_set, sim_set_name)
    await robust_executor.run_safe(sim_set.run)
    return f"Simulation set '{sim_set_name}' in project '{project_name}' started."

async def add_task_to_set(project_name: str, sim_set_name: str, task_project_name: str) -> str:
    """Add a project task to an existing simulation set."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    sim_set = await robust_executor.run_safe(project.simulation_set, sim_set_name)
    # The docs show add_tasks handles one or more task projects
    await robust_executor.run_safe(sim_set.add_tasks, task_project_name)
    return f"Task '{task_project_name}' added to set '{sim_set_name}'."

def register_simset_tools(mcp: FastMCP):
    """Register tools for batch simulation management."""
    mcp.tool()(list_simulation_sets)
    mcp.tool()(run_simulation_set)
    mcp.tool()(add_task_to_set)
