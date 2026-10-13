import asyncio
import glob
import math
import os
import time
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import Context, MCPServer as FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor
from pscad_mcp.utils.sandbox import checked_path, checked_read_tree

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


async def _snapshot_project_outputs(project: Any) -> Optional[Dict[str, tuple]]:
    """Snapshot output files before a run; None means the folder was unavailable."""
    try:
        folder = await robust_executor.run_safe(lambda: project.temp_folder)
        if not isinstance(folder, (str, os.PathLike)) or not folder:
            return None
        folder = checked_read_tree(os.fspath(folder), purpose="PSCAD output tree")
        if not os.path.isdir(folder):
            return None
        snapshot = {}
        for pattern in ("*.psout", "*.out"):
            for path in glob.glob(os.path.join(folder, pattern)):
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                snapshot[os.path.abspath(path)] = (stat.st_mtime_ns, stat.st_size)
        return snapshot
    except Exception:
        # Output location support varies by PSCAD installation and is only
        # needed to confirm a run that begins and ends between status polls.
        return None


async def _project_output_changed(
    project: Any, baseline: Optional[Dict[str, tuple]]
) -> bool:
    """Return whether this run created or modified a PSCAD output file."""
    if baseline is None:
        return False
    current = await _snapshot_project_outputs(project)
    if current is None:
        return False
    return any(
        path not in baseline or baseline[path] != metadata
        for path, metadata in current.items()
    )

async def run_project_to_completion(
    project_name: str,
    ctx: Context,
    timeout_seconds: float = 1800.0,
) -> Dict[str, Any]:
    """Run a PSCAD project to a terminal state and stream bounded progress.

    Idle immediately after start is treated as a startup race, not as a
    terminal result. A transition from building to idle can also mean that a
    short run completed between polls, so build diagnostics are compared with
    a pre-run snapshot before choosing the result. A timeout never cancels PSCAD.
    """
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout_seconds must be a finite number greater than zero.")

    pscad = pscad_manager.pscad
    if not await robust_executor.run_safe(pscad.licensed):
        return {
            "status": "not_started",
            "project": project_name,
            "message": "PSCAD is not licensed.",
        }

    # Do not accidentally attach this request to a run left behind by an
    # earlier request that timed out.
    initial_status = await get_run_status(project_name)
    if initial_status["state"] in {"building", "running"}:
        return {
            "status": "already_running",
            "project": project_name,
            "state": initial_status["state"],
            "message": "A PSCAD build or simulation is already in progress; it was not restarted.",
        }

    # Snapshot diagnostics before start so an old build's errors are not
    # attributed to this run. If diagnostics are unavailable, continue safely
    # but do not treat an unobserved run as confirmed completion.
    baseline_errors = []
    baseline_available = True
    try:
        baseline_errors = list((await get_build_messages(project_name)).get("errors", []))
    except Exception:
        baseline_available = False

    project = await robust_executor.run_safe(pscad.project, project_name)
    baseline_outputs = await _snapshot_project_outputs(project)
    await robust_executor.run_safe(project.start)
    started_at = time.monotonic()
    startup_grace_seconds = min(5.0, timeout_seconds / 2.0)

    async def report(progress: float, message: str) -> None:
        bounded_progress = max(0.0, min(100.0, float(progress)))
        await ctx.report_progress(bounded_progress, total=100, message=message)

    await report(0, f"Started build-and-run for '{project_name}'; waiting for PSCAD status.")

    # Poll quickly after every state transition. Long backoff intervals can
    # otherwise miss an entire short Run phase between two status samples.
    poll_delays = (1, 2, 3, 5, 8, 10)
    poll_index = 0
    saw_building = False
    saw_running = False
    idle_polls = 0
    last_state = "unknown"
    previous_state = None
    last_progress = 0.0

    while True:
        elapsed = time.monotonic() - started_at
        if elapsed >= timeout_seconds:
            await report(
                last_progress,
                f"Timed out after {elapsed:.1f}s while PSCAD state was '{last_state}'. "
                "The simulation may still be running; inspect get_run_status before retrying.",
            )
            return {
                "status": "timeout",
                "project": project_name,
                "elapsed_seconds": round(elapsed, 2),
                "last_state": last_state,
                "message": "Wait timed out; the PSCAD process was not cancelled.",
            }

        status = await get_run_status(project_name)
        raw_state = status["state"]
        last_state = "idle" if raw_state == "idle_or_finished" else raw_state
        state_changed = last_state != previous_state
        if state_changed:
            poll_index = 0
        previous_state = last_state

        if last_state == "building":
            saw_building = True
            idle_polls = 0
            await report(last_progress, f"PSCAD is building '{project_name}'.")
        elif last_state == "running":
            saw_running = True
            idle_polls = 0
            run_progress = status.get("progress")
            if (
                isinstance(run_progress, (int, float))
                and not isinstance(run_progress, bool)
                and math.isfinite(run_progress)
            ):
                last_progress = max(0.0, min(100.0, float(run_progress)))
            await report(last_progress, f"PSCAD is running '{project_name}'.")
        else:
            if saw_running:
                await report(100, f"PSCAD finished running '{project_name}'.")
                return {
                    "status": "completed",
                    "project": project_name,
                    "elapsed_seconds": round(time.monotonic() - started_at, 2),
                    "message": "PSCAD was observed running and has now returned to idle.",
                }

            idle_polls += 1
            elapsed = time.monotonic() - started_at
            if not saw_building and elapsed < startup_grace_seconds and idle_polls < 4:
                await report(
                    last_progress,
                    f"PSCAD is still idle during startup for '{project_name}'; waiting for the run to begin.",
                )
            else:
                try:
                    messages = await get_build_messages(project_name)
                except Exception as exc:
                    await report(
                        last_progress,
                        f"PSCAD returned to idle before a run was observed; diagnostics unavailable: {exc}",
                    )
                    return {
                        "status": "failed",
                        "project": project_name,
                        "saw_building": saw_building,
                        "message": f"Could not read build diagnostics after idle: {exc}",
                    }

                errors = list(messages.get("errors", []))
                # Remove matching pre-run errors one-for-one; retain only errors
                # that appeared during this attempt.
                if baseline_available:
                    remaining_baseline = list(baseline_errors)
                    new_errors = []
                    for error in errors:
                        try:
                            remaining_baseline.remove(error)
                        except ValueError:
                            new_errors.append(error)
                    errors = new_errors

                warnings = messages.get("warnings", [])
                if errors:
                    final_status = "build_failed"
                    message = "PSCAD returned to idle before a run was observed; new build errors were found."
                elif saw_building and baseline_available and await _project_output_changed(project, baseline_outputs):
                    # A short Run phase may occur entirely between polls. A new
                    # or modified output file is independent evidence that the
                    # build-and-run produced results, rather than idle alone.
                    final_status = "completed"
                    message = (
                        "PSCAD entered Build and returned to idle without new build errors; "
                        "a project output file was created or updated during this run."
                    )
                else:
                    final_status = "not_completed"
                    message = (
                        "PSCAD returned to idle before a simulation was observed. "
                        "Completion cannot be confirmed from status, build diagnostics, "
                        "and a fresh output file."
                    )
                await report(100 if final_status == "completed" else last_progress, message)
                return {
                    "status": final_status,
                    "project": project_name,
                    "saw_building": saw_building,
                    "errors": errors,
                    "warnings": warnings,
                    "message": message,
                }

        remaining_seconds = timeout_seconds - (time.monotonic() - started_at)
        if remaining_seconds <= 0:
            continue
        delay = 1 if state_changed else poll_delays[min(poll_index, len(poll_delays) - 1)]
        await asyncio.sleep(min(delay, remaining_seconds))
        if not state_changed:
            poll_index = min(poll_index + 1, len(poll_delays) - 1)


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
