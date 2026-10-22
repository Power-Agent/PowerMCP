from typing import List, Dict, Any, Optional
import asyncio
import os
import time

from mcp.server.mcpserver import MCPServer as FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor
from pscad_mcp.utils.sandbox import checked_path


async def load_projects(filenames: List[str]) -> str:
    """Load projects or workspace into PSCAD."""
    pscad = pscad_manager.pscad
    abs_paths = [
        os.path.abspath(checked_path(filename, purpose="filenames"))
        for filename in filenames
    ]
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

    Uses non-blocking ``Project.start()`` so it returns immediately rather
    than holding the PSCAD worker for the entire simulation. Poll
    ``get_run_status`` or use ``run_project_to_completion`` to wait.
    """
    pscad = pscad_manager.pscad
    if not await robust_executor.run_safe(pscad.licensed):
        return {"started": False, "error": "PSCAD is not licensed."}

    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.start)
    return {
        "started": True,
        "project": project_name,
        "note": "Build+run started. Poll get_run_status or call run_project_to_completion.",
    }


async def run_project_to_completion(
    project_name: str,
    timeout_seconds: float = 1800,
    poll_interval_seconds: float = 1.0,
) -> Dict[str, Any]:
    """Start a PSCAD build+simulation and poll it to a terminal outcome.

    Progress is reported through MCP logging while the project is building or
    running. An idle state only counts as successful completion after this call
    has observed the project running. If it returns idle before running, build
    messages are inspected and the result is reported as failed or not_started,
    never as a fabricated success.

    `timeout_seconds` is an end-to-end deadline. It intentionally does not
    use the executor's watchdog timeout because legitimate PSCAD runs can take
    many minutes. Tests can inject a smaller poll interval and mocked clock.
    """
    if timeout_seconds <= 0:
        return {
            "status": "failed",
            "final_status": "invalid_timeout",
            "project": project_name,
            "message": "timeout_seconds must be greater than zero.",
        }
    if poll_interval_seconds <= 0:
        return {
            "status": "failed",
            "final_status": "invalid_poll_interval",
            "project": project_name,
            "message": "poll_interval_seconds must be greater than zero.",
        }

    pscad = pscad_manager.pscad
    if not await robust_executor.run_safe(pscad.licensed):
        return {
            "status": "failed",
            "final_status": "not_started",
            "started": False,
            "project": project_name,
            "message": "PSCAD is not licensed.",
        }

    project = await robust_executor.run_safe(pscad.project, project_name)
    try:
        await robust_executor.run_safe(project.start)
    except Exception as exc:
        return {
            "status": "failed",
            "final_status": "not_started",
            "started": False,
            "project": project_name,
            "message": f"PSCAD could not start the project: {exc}",
        }

    started_at = time.monotonic()
    deadline = started_at + timeout_seconds
    saw_running = False
    last_progress = None
    next_delay = poll_interval_seconds
    delay_schedule = (1.0, 2.0, 5.0, 10.0)

    while time.monotonic() < deadline:
        try:
            status, progress = await robust_executor.run_safe(
                project.run_status, _timeout=0
            )
        except Exception as exc:
            return {
                "status": "failed",
                "final_status": "status_error",
                "started": True,
                "project": project_name,
                "message": f"Unable to read PSCAD run status: {exc}",
                "saw_running": saw_running,
            }

        raw_status = str(status or "").strip()
        normalized = raw_status.lower()
        if normalized in {"run", "running"}:
            state = "running"
            saw_running = True
        elif normalized in {"build", "building", "compile", "compiling"}:
            state = "building"
        else:
            # PSCAD's non-active status is ambiguous: idle before the first
            # running observation can mean a rejected build or a run that never
            # started. Only after seeing running can this indicate completion.
            if saw_running:
                await _report_progress(
                    project_name, "completed", 100, "Simulation completed."
                )
                return {
                    "status": "completed",
                    "final_status": "completed",
                    "started": True,
                    "project": project_name,
                    "progress": 100,
                    "raw_status": raw_status,
                    "elapsed_seconds": round(time.monotonic() - started_at, 3),
                }

            messages = await _read_build_messages(project)
            errors, warnings = _split_messages(messages)
            if errors:
                final_status = "build_failed"
                message = "PSCAD returned to idle before simulation started and reported build errors."
            else:
                final_status = "not_started"
                message = (
                    "PSCAD returned to idle before simulation started; no build "
                    "errors were reported, so completion cannot be confirmed."
                )
            await _report_progress(project_name, final_status, 0, message)
            return {
                "status": "failed",
                "final_status": final_status,
                "started": False,
                "project": project_name,
                "message": message,
                "errors": errors,
                "warnings": warnings,
                "raw_status": raw_status,
                "elapsed_seconds": round(time.monotonic() - started_at, 3),
            }

        try:
            progress_value = float(progress) if progress is not None else None
        except (TypeError, ValueError):
            progress_value = None
        if progress_value is not None:
            progress_value = max(0.0, min(100.0, progress_value))
        if progress_value != last_progress or state == "building":
            await _report_progress(
                project_name, state, progress_value, f"PSCAD {state}."
            )
            last_progress = progress_value

        elapsed = time.monotonic() - started_at
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        # Back off while progress is unchanged; reset on progress/state changes.
        if progress_value != last_progress:
            next_delay = poll_interval_seconds
        else:
            next_delay = min(
                next_delay if next_delay > 0 else poll_interval_seconds,
                delay_schedule[-1],
            )
            if next_delay < delay_schedule[-1]:
                next_delay = delay_schedule[
                    min(delay_schedule.index(next_delay) + 1, len(delay_schedule) - 1)
                ] if next_delay in delay_schedule else min(next_delay * 2, delay_schedule[-1])
        await asyncio.sleep(min(next_delay, remaining))

    return {
        "status": "failed",
        "final_status": "timeout",
        "started": True,
        "project": project_name,
        "message": f"Simulation did not reach a terminal state within {timeout_seconds:g} seconds.",
        "saw_running": saw_running,
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
    }


async def _report_progress(project_name: str, state: str, progress: Optional[float], message: str) -> None:
    """Stream progress to clients that support MCP logging; tolerate no logging session."""
    try:
        from mcp.server.lowlevel.server import request_ctx

        ctx = request_ctx.get()
        await ctx.session.send_log_message(
            level="info",
            data={
                "project": project_name,
                "state": state,
                "progress": progress,
                "message": message,
            },
            logger="pscad.run",
        )
    except (LookupError, AttributeError, RuntimeError, ValueError):
        # Direct calls and clients without a logging-capable session still get
        # meaningful polling results; progress reporting must not break a run.
        return


async def _read_build_messages(project: Any) -> List[Any]:
    """Read build diagnostics after a run returns idle before starting."""
    try:
        return await robust_executor.run_safe(project.messages, _timeout=0) or []
    except Exception:
        return []


async def build_project(project_name: str, clean: bool = True) -> Dict[str, Any]:
    """Build (compile) a project without running it, and report any messages."""
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
    """Get simulation progress and a derived high-level state."""
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
    name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Find components matching criteria in a project."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    components = await robust_executor.run_safe(
        project.find_all, definition=definition, name=name
    )
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
        except Exception as exc:
            validation_results[param_name] = {"valid": False, "error": str(exc)}

    return validation_results


async def get_project_settings(project_name: str) -> Dict[str, Any]:
    """Get simulation run parameters for a project."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    settings = await robust_executor.run_safe(project.parameters)
    return settings if settings else {}


async def set_project_settings(project_name: str, settings: Dict[str, Any]) -> str:
    """Update project settings."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    await robust_executor.run_safe(project.parameters, **settings)
    return f"Settings updated for project '{project_name}'."


def register_project_tools(mcp: FastMCP):
    """Register tools for managing projects and components."""
    mcp.tool()(load_projects)
    mcp.tool()(list_projects)
    mcp.tool()(run_project)
    mcp.tool()(run_project_to_completion)
    mcp.tool()(build_project)
    mcp.tool()(get_run_status)
    mcp.tool()(get_build_messages)
    mcp.tool()(find_components)
    mcp.tool()(get_component_parameters)
    mcp.tool()(set_component_parameters)
    mcp.tool()(validate_component_parameters)
    mcp.tool()(get_project_settings)
    mcp.tool()(set_project_settings)
