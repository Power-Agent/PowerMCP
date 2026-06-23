from typing import List, Dict, Any, Optional
import os
from mcp.server.fastmcp import FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor

async def load_projects(filenames: List[str]) -> str:
    """Load projects or workspace into PSCAD."""
    pscad = pscad_manager.pscad
    abs_paths = [os.path.abspath(f) for f in filenames]
    # Parsing a large .pscx (the MMC case is ~1.1 MB) can exceed the default
    # 30 s watchdog, so give loading a generous timeout.
    await robust_executor.run_safe(pscad.load, *abs_paths, _timeout=120)
    return f"Loaded: {', '.join(abs_paths)}"

async def list_projects() -> List[Dict[str, str]]:
    """List all projects in the workspace."""
    pscad = pscad_manager.pscad
    return await robust_executor.run_safe(pscad.projects)

async def run_project(project_name: str) -> Dict[str, Any]:
    """Start a (build &) simulation for a given project, without blocking.

    Uses the non-blocking ``Project.start()`` (focuses the project, then fires
    the run) so this call returns immediately rather than holding the single
    PSCAD worker for the entire multi-minute build+run. Poll ``get_run_status``
    to follow progress: it transitions ``building`` -> ``running`` ->
    ``idle_or_finished``. If it returns to ``idle_or_finished`` without ever
    reporting ``running``, the build failed -- call ``get_build_messages`` and
    ``get_project_output`` to see why (e.g. a missing Fortran compiler).
    """
    pscad = pscad_manager.pscad
    if not await robust_executor.run_safe(pscad.licensed):
        return {"started": False, "error": "PSCAD is not licensed."}

    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.start)
    return {
        "started": True,
        "project": project_name,
        "note": "Build+run started. Poll get_run_status until state is 'idle_or_finished'.",
    }

async def build_project(project_name: str, clean: bool = True) -> Dict[str, Any]:
    """Build (compile) a project without running it, and report any messages.

    This is a blocking compile used as a pre-flight check: it surfaces compiler
    and link errors (for example a missing/misconfigured Fortran compiler)
    before committing to a long simulation. The watchdog is disabled for the
    build, so no other PSCAD call can run until it finishes.
    """
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    builder = project.build if clean else project.build_modified
    await robust_executor.run_safe(builder, _timeout=0)
    messages = await robust_executor.run_safe(project.messages)
    errors, warnings = _split_messages(messages)
    return {
        "built": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

async def get_run_status(project_name: str) -> Dict[str, Any]:
    """Get simulation progress and a derived high-level state.

    ``state`` is one of ``building`` (compiling), ``running`` (simulating, with
    ``progress`` 0-100), or ``idle_or_finished`` (not building or running --
    i.e. completed, not yet started, or failed).
    """
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    status, progress = await robust_executor.run_safe(project.run_status)
    if status == "Build":
        state = "building"
    elif status == "Run":
        state = "running"
    else:
        state = "idle_or_finished"
    return {"state": state, "raw_status": status, "progress": progress}

async def get_build_messages(project_name: str) -> Dict[str, Any]:
    """Return the load/build messages for a project, split into errors/warnings."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    messages = await robust_executor.run_safe(project.messages)
    errors, warnings = _split_messages(messages)
    info_count = len(messages) - len(errors) - len(warnings)
    return {"errors": errors, "warnings": warnings, "info_count": info_count}

def _split_messages(messages: Any) -> tuple:
    """Split PSCAD build messages into (errors, warnings) lists of dicts."""
    errors, warnings = [], []
    for msg in messages or []:
        status = str(getattr(msg, "status", "")).lower()
        entry = {
            "text": getattr(msg, "text", str(msg)),
            "component": getattr(msg, "name", None),
            "status": getattr(msg, "status", None),
        }
        if "error" in status:
            errors.append(entry)
        elif "warn" in status:
            warnings.append(entry)
    return errors, warnings

async def find_components(
    project_name: str, 
    definition: Optional[str] = None, 
    name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find components matching criteria in a project."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    components = await robust_executor.run_safe(project.find_all, definition=definition, name=name)
    return [{"id": c.id, "name": c.name, "definition": c.definition} for c in components]

async def get_component_parameters(project_name: str, component_id: int) -> Dict[str, Any]:
    """Get all parameter values for a specific component by its ID."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    component = await robust_executor.run_safe(project.component, component_id)
    params = await robust_executor.run_safe(component.parameters)
    return params if params else {}

async def set_component_parameters(project_name: str, component_id: int, parameters: Dict[str, Any]) -> str:
    """Set parameter values for a specific component."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    component = await robust_executor.run_safe(project.component, component_id)
    await robust_executor.run_safe(component.parameters, parameters=parameters)
    return f"Parameters updated for component {component_id}."

async def validate_component_parameters(project_name: str, component_id: int, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate if the given parameters are within the legal range for a component."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    component = await robust_executor.run_safe(project.component, component_id)
    
    validation_results = {}
    for param_name, value in parameters.items():
        try:
            legal_range = await robust_executor.run_safe(component.range, param_name)
            validation_results[param_name] = {"valid": True, "range": str(legal_range)}
        except Exception as e:
            validation_results[param_name] = {"valid": False, "error": str(e)}
            
    return validation_results

async def get_project_settings(project_name: str) -> Dict[str, Any]:
    """Get all settings (run parameters) for a project.

    Includes keys such as ``time_step``, ``time_duration``, ``sample_step``,
    ``PlotType`` ("NONE"/"OUT"/"PSOUT"), ``StartType``, ``SnapType`` and
    ``MrunType``.
    """
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    settings = await robust_executor.run_safe(project.parameters)
    return settings if settings else {}

async def set_project_settings(project_name: str, settings: Dict[str, Any]) -> str:
    """Update project settings (run parameters).

    For example ``{"PlotType": "PSOUT"}`` to write a consolidated .psout output
    file, or ``{"time_duration": 5.0}`` to change the run length.
    """
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.parameters, **settings)
    return f"Settings updated for project '{project_name}'."

def register_project_tools(mcp: FastMCP):
    """Register tools for managing projects and components."""
    mcp.tool()(load_projects)
    mcp.tool()(list_projects)
    mcp.tool()(run_project)
    mcp.tool()(build_project)
    mcp.tool()(get_run_status)
    mcp.tool()(get_build_messages)
    mcp.tool()(find_components)
    mcp.tool()(get_component_parameters)
    mcp.tool()(set_component_parameters)
    mcp.tool()(validate_component_parameters)
    mcp.tool()(get_project_settings)
    mcp.tool()(set_project_settings)
