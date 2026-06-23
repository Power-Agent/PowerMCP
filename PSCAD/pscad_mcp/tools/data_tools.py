from typing import Dict, Any, List, Optional, Union
import os
import glob
import math
import logging
from mcp.server.fastmcp import FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.executor import robust_executor

logger = logging.getLogger("pscad-mcp.data")


async def get_project_output(project_name: str) -> str:
    """Get the text output messages from the PSCAD project's runtime."""
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, project_name)
    return await robust_executor.run_safe(project.output)


async def _resolve_psout(name_or_file: str) -> str:
    """Resolve a project name or path to an absolute ``.psout`` file path.

    Accepts either a direct path to a ``.psout`` file or a loaded project's
    name. For a project name, the newest ``.psout`` in the project's
    compiler-dependent temp folder is returned (that is where EMTDC writes the
    consolidated binary output). Raises ``FileNotFoundError`` with the searched
    locations if nothing is found.
    """
    candidate = os.path.abspath(name_or_file)
    if os.path.isfile(candidate):
        if candidate.lower().endswith(".psout"):
            return candidate
        if candidate.lower().endswith(".out"):
            # The legacy .out ASCII format is not readable by mhi.psout; prefer a
            # sibling .psout written by the same run, if present.
            siblings = glob.glob(os.path.join(os.path.dirname(candidate), "*.psout"))
            if siblings:
                return max(siblings, key=os.path.getmtime)
            return candidate  # let mhi.psout.File raise a clear error

    # Treat as a project name: locate the newest .psout in its temp folder.
    pscad = pscad_manager.pscad
    project = await robust_executor.run_safe(pscad.project, name_or_file)
    searched: List[str] = []
    temp_folder: Optional[str] = None
    try:
        temp_folder = await robust_executor.run_safe(lambda: project.temp_folder)
    except Exception as e:  # pragma: no cover - depends on live PSCAD
        logger.warning("Could not read temp_folder for %s: %s", name_or_file, e)

    for folder in filter(None, [temp_folder]):
        searched.append(folder)
        matches = glob.glob(os.path.join(folder, "*.psout"))
        if matches:
            return max(matches, key=os.path.getmtime)

    raise FileNotFoundError(
        f"No .psout file found for project '{name_or_file}'. "
        f"Searched: {searched or '[temp folder unavailable]'}. "
        "Ensure the run has finished and the project's output format is PSOUT."
    )


def _meta(call, key):
    """Read a variable from a call node (Name/Unit/Group live on the PGB call)."""
    if call is None:
        return None
    try:
        return call.get(key)
    except Exception:  # pragma: no cover - defensive
        return None


def _iter_traces(run):
    """Yield (pgb_call, trace, path) triples for every data trace in the run.

    PSCAD .psout files organise output as ``PGB`` nodes (the user-facing
    channel, carrying Name/Unit/Group) each with a ``Data`` record whose
    children are the actual ``Trace`` data columns (a multi-phase signal has
    several traces under one PGB). The library's ``[@Source='Trace']`` filter
    does not match this nesting, so we walk the whole call tree once, index the
    PGB nodes, and attach each trace to its PGB grandparent via the path. The
    friendly metadata therefore comes from ``pgb_call``; the samples come from
    ``trace``. Falls back to positional enumeration if no traces are found.
    """
    f = run.file
    sep = getattr(f, "_sep", "/")
    pgb_by_path = {}
    trace_calls = []
    try:
        for call, path in f.call_paths("**"):
            source = call.get("Source")
            if source == "PGB":
                pgb_by_path[path] = call
            elif source == "Trace":
                trace_calls.append((call, path))
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("call_paths('**') failed (%s); falling back to positional traces", e)

    if trace_calls:
        for call, path in trace_calls:
            parts = path.split(sep)
            # trace path is <PGB path>/<record>/<trace#>; drop the last two.
            parent = sep.join(parts[:-2]) if len(parts) > 2 else path
            yield pgb_by_path.get(parent), run.trace(call), path
        return

    for i, trace in enumerate(run.traces()):
        yield None, trace, f"#{i}"


def _summarize(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"count": 0}
    fvals = [float(v) for v in values]
    total = math.fsum(fvals)
    sq = math.fsum(v * v for v in fvals)
    return {
        "count": n,
        "min": min(fvals),
        "max": max(fvals),
        "mean": total / n,
        "final": fvals[-1],
        "rms": math.sqrt(sq / n),
    }


def _match_channel(path: str, name: Optional[str], wanted: List[str]) -> Optional[str]:
    """Return the requested identifier that matches this trace, or None.

    Matching, in priority order: exact path, exact name, exact name
    (case-insensitive), path endswith identifier.
    """
    sname = None if name is None else str(name)
    for w in wanted:
        if w == path or (sname is not None and w == sname):
            return w
    for w in wanted:
        if sname is not None and w.lower() == sname.lower():
            return w
        if path and path.endswith(w):
            return w
    return None


async def list_output_channels(name_or_file: str, run_index: int = 0) -> Dict[str, Any]:
    """List the output channels (traces) available in a project's .psout file.

    Returns lightweight metadata only (path, name, description, unit, group,
    sample count) -- not the data itself -- so it is safe to call on files with
    hundreds of channels. Pass a loaded project's name or a direct path to a
    ``.psout`` file. Use the returned ``path`` values with
    ``read_output_channels`` to fetch data.
    """
    try:
        import mhi.psout
    except ImportError:
        return {"error": "mhi-psout package not installed."}

    try:
        path = await _resolve_psout(name_or_file)
    except Exception as e:
        return {"error": str(e)}

    channels: List[Dict[str, Any]] = []
    try:
        with mhi.psout.File(path) as f:
            num_runs = f.num_runs
            run = f.run(run_index)
            for call, trace, pth in _iter_traces(run):
                channels.append({
                    "path": pth,
                    "name": _meta(call, "Name"),
                    "desc": _meta(call, "Desc"),
                    "unit": _meta(call, "Unit"),
                    "group": _meta(call, "Group"),
                    "samples": getattr(trace, "size", None),
                })
    except Exception as e:
        return {"error": str(e), "file": path}

    return {
        "file": path,
        "num_runs": num_runs,
        "channel_count": len(channels),
        "channels": channels,
    }


async def read_output_channels(
    name_or_file: str,
    channels: Union[List[str], str],
    run_index: int = 0,
    summary: bool = True,
    max_points: int = 2000,
) -> Dict[str, Any]:
    """Read selected output channels from a project's .psout file.

    ``channels`` must be an explicit list of identifiers (channel ``path`` or
    ``name`` from ``list_output_channels``) -- this guards against accidentally
    pulling every channel (a file may hold hundreds of channels with tens of
    thousands of samples each). For each channel this returns summary statistics
    (``min/max/mean/final/rms``) and a downsampled preview of at most
    ``max_points`` (time, value) points.
    """
    try:
        import mhi.psout
    except ImportError:
        return {"error": "mhi-psout package not installed."}

    if isinstance(channels, str):
        channels = [channels]
    if not channels:
        return {"error": "Specify a 'channels' list (see list_output_channels); "
                         "refusing to read all channels at once."}
    if len(channels) > 30:
        return {"error": f"Too many channels requested ({len(channels)}); cap is 30. "
                         "Read in smaller batches."}
    max_points = max(1, min(int(max_points or 2000), 5000))

    try:
        path = await _resolve_psout(name_or_file)
    except Exception as e:
        return {"error": str(e)}

    wanted = list(channels)
    result: Dict[str, Any] = {}
    matched = set()
    sample_count: Optional[int] = None
    try:
        with mhi.psout.File(path) as f:
            run = f.run(run_index)
            for call, trace, pth in _iter_traces(run):
                name = _meta(call, "Name")
                key = _match_channel(pth, name, wanted)
                if key is None or key in matched:
                    continue
                matched.add(key)
                y = list(trace.data)
                try:
                    domain = trace.domain
                    t = list(domain.data) if domain is not None else []
                except Exception:
                    t = []
                sample_count = len(y)
                step = max(1, len(y) // max_points)
                entry: Dict[str, Any] = {
                    "path": pth,
                    "name": name,
                    "unit": _meta(call, "Unit"),
                    "preview": {
                        "step": step,
                        "time": [float(v) for v in t[::step]] if t else [],
                        "values": [float(v) for v in y[::step]],
                    },
                }
                if summary:
                    entry["summary"] = _summarize(y)
                result[key] = entry
    except Exception as e:
        return {"error": str(e), "file": path}

    not_found = [c for c in wanted if c not in matched]
    return {
        "file": path,
        "run_index": run_index,
        "sample_count": sample_count,
        "channels": result,
        "not_found": not_found,
    }


async def read_output_file(file_path: str, summary: bool = True) -> Dict[str, Any]:
    """Read a .psout results file (back-compatible direct-path entry point).

    Returns per-channel metadata, and summary statistics when ``summary`` is
    True. It deliberately never returns the full sample arrays; use
    ``read_output_channels`` to fetch (downsampled) data for selected channels.
    """
    try:
        import mhi.psout
    except ImportError:
        return {"error": "mhi-psout package not installed."}

    try:
        path = await _resolve_psout(file_path)
    except Exception as e:
        return {"error": str(e)}

    channels: Dict[str, Any] = {}
    try:
        with mhi.psout.File(path) as f:
            run = f.run(0)
            for call, trace, pth in _iter_traces(run):
                entry: Dict[str, Any] = {
                    "name": _meta(call, "Name"),
                    "unit": _meta(call, "Unit"),
                }
                if summary:
                    entry["summary"] = _summarize(list(trace.data))
                channels[pth] = entry
    except Exception as e:
        return {"error": str(e), "file": path}

    return {"file": path, "channel_count": len(channels), "channels": channels}


def register_data_tools(mcp: FastMCP):
    """Register tools for reading simulation results and output."""
    mcp.tool()(get_project_output)
    mcp.tool()(list_output_channels)
    mcp.tool()(read_output_channels)
    mcp.tool()(read_output_file)
