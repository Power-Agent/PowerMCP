from typing import List, Dict, Any, Optional
import asyncio
import os
from mcp.server.fastmcp import FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor
from pscad_mcp.core.errors import (
    ErrorKind,
    err,
    err_from_exc,
    ok,
    values_equivalent,
)

async def load_projects(filenames: List[str]) -> str:
    """Load projects or workspace into PSCAD."""
    pscad = pscad_manager.pscad
    abs_paths = [os.path.abspath(f) for f in filenames]
    await robust_executor.run_safe(pscad.load, *abs_paths)
    return f"Loaded: {', '.join(abs_paths)}"

async def list_projects() -> List[Dict[str, str]]:
    """List all projects in the workspace."""
    pscad = pscad_manager.pscad
    return await robust_executor.run_safe(pscad.projects)

async def run_project(project_name: str) -> str:
    """Start simulation for a given project."""
    pscad = pscad_manager.pscad
    if not pscad.licensed():
        return "Error: PSCAD is not licensed."
    
    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.run)
    return f"Simulation started for '{project_name}'."

async def get_run_status(project_name: str) -> Dict[str, Any]:
    """Get simulation progress and state."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    status, progress = await robust_executor.run_safe(project.run_status)
    return {"status": status, "progress": progress}

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
    """Get all settings for a project."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    settings = await robust_executor.run_safe(project.settings)
    return settings if settings else {}

async def set_project_settings(project_name: str, settings: Dict[str, Any]) -> str:
    """Update project settings."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.settings, **settings)
    return f"Settings updated for project '{project_name}'."

async def run_project_and_wait(
    project_name: str,
    timeout_s: float = 300.0,
    initial_poll_s: float = 0.5,
    max_poll_s: float = 10.0,
    ctx: Optional[Any] = None,
) -> Dict[str, Any]:
    try:
        pscad = pscad_manager.pscad
    except Exception as e:
        return err_from_exc(e)

    try:
        if not pscad.licensed():
            return err(ErrorKind.LICENSE, "PSCAD is not licensed.")
    except Exception as e:
        return err_from_exc(e)

    try:
        project = await robust_executor.run_safe(pscad.project, project_name)
    except Exception as e:
        return err_from_exc(e)

    try:
        await robust_executor.run_safe(project.run)
    except Exception as e:
        return err_from_exc(e)

    loop = asyncio.get_running_loop()
    started = loop.time()
    poll_interval = initial_poll_s
    last_status: Any = None
    last_progress: Any = None
    last_reported_progress: Any = -1

    while True:
        elapsed = loop.time() - started
        if elapsed > timeout_s:
            return err(
                ErrorKind.TIMEOUT,
                f"Run did not complete within {timeout_s}s. "
                f"Last status: ({last_status!r}, {last_progress!r}).",
            )

        try:
            last_status, last_progress = await robust_executor.run_safe(project.run_status)
        except Exception as e:
            return err_from_exc(e)

        if last_status is None:
            break

        if (
            ctx is not None
            and last_progress is not None
            and last_progress != last_reported_progress
        ):
            try:
                await ctx.report_progress(last_progress, 100)
            except Exception:
                pass
            last_reported_progress = last_progress

        await asyncio.sleep(poll_interval)

        if elapsed > 60:
            poll_interval = min(poll_interval * 1.5, max_poll_s)
        elif last_progress is not None:
            poll_interval = min(max(poll_interval, 2.0), max_poll_s)
        else:
            poll_interval = min(poll_interval * 1.2, max_poll_s)

    runtime_s = round(loop.time() - started, 2)

    output_messages = ""
    try:
        output_messages = await robust_executor.run_safe(project.output)
    except Exception:
        # Some PSCAD runs complete without exposing output through the API.
        pass

    output_file_path: Optional[str] = None
    try:
        settings = await robust_executor.run_safe(project.settings)
        if settings:
            output_file_path = settings.get("output_filename")
    except Exception:
        # Output metadata is useful but not required for a successful run.
        pass

    return ok({
        "final_status": "completed",
        "runtime_s": runtime_s,
        "output_messages": output_messages,
        "output_file_path": output_file_path,
    })


async def set_component_parameters_safe(
    project_name: str,
    component_id: int,
    parameters: Dict[str, Any],
    rollback_on_mismatch: bool = True,
) -> Dict[str, Any]:
    try:
        pscad = pscad_manager.pscad
    except Exception as e:
        return err_from_exc(e)

    try:
        project = await robust_executor.run_safe(pscad.project, project_name)
    except Exception as e:
        return err_from_exc(e)

    try:
        component = await robust_executor.run_safe(project.component, component_id)
    except Exception as e:
        return err_from_exc(e)

    invalid: Dict[str, str] = {}
    for name in parameters.keys():
        try:
            await robust_executor.run_safe(component.range, name)
        except Exception as e:
            invalid[name] = str(e)
    if invalid:
        return err(
            ErrorKind.PARAM_INVALID,
            f"Parameter validation failed: {invalid}",
        )

    try:
        snapshot = await robust_executor.run_safe(component.parameters) or {}
    except Exception as e:
        return err_from_exc(e)

    try:
        await robust_executor.run_safe(component.parameters, parameters=parameters)
    except Exception as e:
        return err_from_exc(e)

    try:
        after = await robust_executor.run_safe(component.parameters) or {}
    except Exception as e:
        return err_from_exc(e)

    mismatches: Dict[str, Dict[str, Any]] = {}
    normalized: Dict[str, Any] = {}
    for name, requested in parameters.items():
        stored = after.get(name)
        normalized[name] = stored
        if not values_equivalent(requested, stored):
            mismatches[name] = {"requested": requested, "stored": stored}

    if mismatches and rollback_on_mismatch:
        rollback_status = "applied"
        try:
            rollback_params = {
                k: snapshot[k] for k in parameters.keys() if k in snapshot
            }
            if rollback_params:
                await robust_executor.run_safe(
                    component.parameters, parameters=rollback_params
                )
        except Exception as e:
            rollback_status = f"failed: {e}"
        return err(
            ErrorKind.PARAM_INVALID,
            f"Read-back mismatch on {list(mismatches.keys())}. "
            f"Rollback {rollback_status}. Mismatches: {mismatches}",
        )

    return ok({
        "applied": list(parameters.keys()),
        "normalized_values": normalized,
        "mismatches": mismatches,
    })


def register_project_tools(mcp: FastMCP):
    """Register tools for managing projects and components."""
    mcp.tool()(load_projects)
    mcp.tool()(list_projects)
    mcp.tool()(run_project)
    mcp.tool()(run_project_and_wait)
    mcp.tool()(get_run_status)
    mcp.tool()(find_components)
    mcp.tool()(get_component_parameters)
    mcp.tool()(set_component_parameters)
    mcp.tool()(set_component_parameters_safe)
    mcp.tool()(validate_component_parameters)
    mcp.tool()(get_project_settings)
    mcp.tool()(set_project_settings)
