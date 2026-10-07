"""
MCP Server — DIgSILENT PowerFactory Control
============================================
Exposes DIgSILENT PowerFactory simulation as FastMCP tools.

Author
------
  Andrea Pomarico
  Aswin Krishna Poyil

Tools
-----
  ping                                  Connectivity check.
  get_config                            Return simulation_config.json as a JSON string.
  get_active_project                    Return the active PowerFactory project.
  get_active_study_case                 Return the active PowerFactory study case.
  get_parameters                        Read selected attributes from matching objects.
  list_objects                          List objects using a PowerFactory object query.
  list_components                       List objects using friendly equipment categories.
  list_study_cases                      List study cases and identify the active case.
  list_contingencies                    List EvtOutage/EvtSwitch/EvtShc fault-case events.
  create_contingency                    Create an idempotent switch-based contingency definition.
  get_contingency_configuration         Read the active ComSimoutage settings.
  configure_contingency_screening       Configure persistent ComSimoutage screening criteria.
  add_contingency_result_variables      Add variables to AC/DC result recording.
  remove_contingency_result_variables   Remove variables from AC/DC result recording.
  import_project                        Import a .pfd file and activate it in PowerFactory.
  create_study_case                     Create/activate a study case by name (no simulation run).
  modify_parameter                      Modify an object attribute by object query + variable name.
  add_component                         Create a bus, load, generator, line, or transformer.
  delete_component                      Preview or delete an exactly named grid component.
  run_loadflow                          Run a load flow calculation (ComLdf) on the active study case.
  run_short_circuit                     Run a short-circuit calculation (ComShc) on the active study case.
  run_contingency_analysis              Execute ComSimoutage with an optional method.
  get_contingency_results               Read/filter bounded AC or DC contingency results.
  get_contingency_summary               Summarize contingency overloads and voltage violations.
  run_simulation                        Run the full pipeline from simulation_config.json.
  run_custom_case                       Run a one-off case with parameters supplied at call-time.
  read_results_csv                      Read the latest (or a specific) RMS results CSV.

Usage
-----
    python MCP_PowerFactory.py                      # stdio transport (default)
    python MCP_PowerFactory.py --transport sse      # SSE transport on port 8000
"""

import sys
import os
import json
import math
import time
import concurrent.futures
from datetime import datetime
from typing import Any

# ── Windows UTF-8 fix ─────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Redirect print() → stderr so output never corrupts MCP frames ─────────────
import builtins as _bt

def _stderr_print(*args, _p=_bt.print, **kwargs):
    kwargs.setdefault("file", sys.stderr)
    _p(*args, **kwargs)

_bt.print = _stderr_print
del _bt

# ── MCP server ────────────────────────────────────────────────────────────────
from mcp.server.mcpserver import MCPServer as FastMCP

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import (
        checked_path,
        checked_read_tree,
        ensure_checked_directory,
    )
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

mcp = FastMCP(
    name="DIgSILENT PowerFactory Control",
    instructions=(
        "Controls DIgSILENT PowerFactory RMS transient-stability simulations. "
        "Runs simulations and saves results (CSV, grid graph PNG) to disk."
    ),
)

_HERE = os.path.dirname(os.path.abspath(__file__))
_MAX_AFFECTED_ELEMENT_SCAN = 10_000


def _ensure_checked_directory(path: str, purpose: str) -> str:
    """Compatibility wrapper for the shared generated-directory helper."""
    return ensure_checked_directory(path, purpose=purpose)


def _default_cfg_path():
    """Resolve the user-writable default config path (lazily, never at import).

    Uses the powermcp config key ``powerfactory.config_path`` when set, otherwise
    ``~/.powermcp/powerfactory/simulation_config.json``. On first use the bundled
    ``simulation_config.example.json`` is copied there if the destination does not
    yet exist (the packaged copy is read-only).
    """
    import os, shutil
    p = None
    try:
        from powermcp.config import get_path
        p = get_path("powerfactory", "config_path", must_exist=False)
    except Exception:
        pass
    if p:
        return checked_path(p, purpose="config path")
    base = os.path.join(os.path.expanduser("~"), ".powermcp", "powerfactory")
    base = _ensure_checked_directory(base, "generated config directory")
    dest = os.path.join(base, "simulation_config.json")
    dest = checked_path(dest, purpose="generated config path", for_write=True)
    example = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation_config.example.json")
    if not os.path.exists(dest) and os.path.exists(example):
        shutil.copyfile(example, dest)
    return dest

# ── Single dedicated thread for ALL PowerFactory API calls ────────────────────
# PowerFactory's Python API requires every call to originate from the same
# thread that called GetApplicationExt(). FastMCP dispatches tool handlers on
# whatever thread the async runtime provides, so we funnel every PF operation
# through this one persistent thread via submit().result().
_pf_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="pf_thread"
)


def _pf(fn, *args, **kwargs):
    """Run fn(*args, **kwargs) on the dedicated PowerFactory thread."""
    return _pf_executor.submit(fn, *args, **kwargs).result()


def _agent_result(method_name: str, *args, structured: bool = False) -> str:
    _, DIgSILENTAgent = _load_modules()
    result = _pf(
        getattr(DIgSILENTAgent, method_name),
        *args,
    )
    if structured:
        return json.dumps(result)
    ok, message = result
    return json.dumps({"success": ok, "message": message})


def _load_modules():
    """Deferred import — avoids startup crash when PowerFactory is not running."""
    from Agent_DIgSILENT import SimulationConfig, DIgSILENTAgent
    return SimulationConfig, DIgSILENTAgent


def _read_only_result(agent, operation):
    """Run a read-only operation and return failures as result data."""
    try:
        app = agent._get_application(open_digsilent=False)
    except Exception as exc:
        return {
            "success": False,
            "message": f"PowerFactory connection failed: {exc}",
        }
    try:
        return operation(app)
    except Exception as exc:
        return {
            "success": False,
            "message": f"PowerFactory read failed: {exc}",
        }


def _to_json(obj: Any) -> str:
    """Recursively sanitise and serialise a result dict to a JSON string."""
    import math
    try:
        import numpy as np
        _np = np
    except ImportError:
        _np = None

    def _clean(o):
        if _np is not None:
            if isinstance(o, _np.ndarray):
                return [_clean(v) for v in o.tolist()]
            if isinstance(o, _np.integer):
                return int(o)
            if isinstance(o, _np.floating):
                v = float(o)
                return None if (math.isnan(v) or math.isinf(v)) else v
            if isinstance(o, _np.bool_):
                return bool(o)
        if isinstance(o, dict):
            return {(str(k) if not isinstance(k, str) else k): _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, float):
            return None if (math.isnan(o) or math.isinf(o)) else o
        if isinstance(o, (str, int, bool, type(None))):
            return o
        return str(o)

    return json.dumps(_clean(obj), indent=2, ensure_ascii=False)


def _object_summary(obj):
    """Return the stable identity fields shared by PowerFactory objects."""
    if obj is None:
        return None
    return {
        "name": obj.GetAttribute("loc_name"),
        "class_name": obj.GetClassName(),
        "full_name": obj.GetFullName(),
    }


def _attribute(obj, name, default=None):
    """Read an optional PowerFactory attribute."""
    try:
        return obj.GetAttribute(name)
    except Exception:
        return default


def _existing_contingency_command(app):
    """Find an existing command without GetFromStudyCase's creation side effect."""
    case = app.GetActiveStudyCase()
    if case is None:
        return None
    commands = case.GetContents("*.ComSimoutage", 0) or []
    if len(commands) > 1:
        raise ValueError("Multiple ComSimoutage commands exist; select a study case with one command")
    return commands[0] if commands else None


def _result_cells(app, result_file, row_count, columns, deadline):
    """Read selected columns in bulk, with a sparse/cell fallback."""
    selected = set(columns)
    vector = None
    try:
        current_user = app.GetCurrentUser()
        vector = current_user.CreateObject(
            "IntVec", f"PowerMCP result read {time.time_ns()}"
        )
        if vector is not None and callable(getattr(result_file, "GetColumnValues", None)):
            rows = [{} for _ in range(row_count)]
            for column in columns:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Result read time budget exceeded; reduce rows/columns or filter variables"
                    )
                code = result_file.GetColumnValues(vector, column)
                if code not in (0, None):
                    raise RuntimeError(f"ElmRes.GetColumnValues returned error code {code}")
                values = vector.GetAttribute("V") or []
                for row, value in enumerate(values[:row_count]):
                    rows[row][column] = (0, value)
            return rows
    except TimeoutError:
        raise
    except Exception:
        pass
    finally:
        if vector is not None:
            try:
                vector.Delete()
            except Exception:
                pass

    sparse = callable(getattr(result_file, "GetFirstValidVariable", None)) and callable(
        getattr(result_file, "GetNextValidVariable", None)
    )
    if not sparse and row_count * len(selected) > 2000:
        raise ValueError("Result interface lacks sparse readers; request at most 2,000 cells")
    rows = []
    for row in range(row_count):
        if time.monotonic() >= deadline:
            raise TimeoutError("Result read time budget exceeded; reduce rows/columns or filter variables")
        cells = {}
        if sparse and selected:
            column = result_file.GetFirstValidVariable(row)
            previous = -1
            while column >= 0 and column <= max(selected):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Result read time budget exceeded; reduce rows/columns or filter variables")
                if column <= previous:
                    raise ValueError("Sparse result iterator did not advance")
                if column in selected:
                    cells[column] = _decode_cell(result_file.GetValue(row, column))
                previous = column
                column = result_file.GetNextValidVariable()
        elif not sparse:
            for column in selected:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Result read time budget exceeded; reduce rows/columns or filter variables")
                cells[column] = _decode_cell(result_file.GetValue(row, column))
        rows.append(cells)
    return rows


def _filtered_result_columns(
    app, result_file, total_columns, variables, column_limit, deadline,
):
    """Resolve filtered columns from IntMon selections instead of scanning ElmRes."""
    columns = {}
    errors = []

    # b:i_obj maps result rows to contingency objects. It is normally the first
    # column; keep the probe bounded so large files do not recreate the slow
    # full metadata scan this helper avoids.
    for column in range(min(total_columns, 16)):
        if time.monotonic() >= deadline:
            raise TimeoutError("Result metadata time budget exceeded")
        if result_file.GetVariable(column) == "b:i_obj":
            item = {"index": column, "variable": "b:i_obj", "object": None}
            try:
                result_object = result_file.GetObject(column)
                if result_object is not None:
                    item["object"] = _object_summary(result_object)
            except Exception:
                pass
            columns[column] = item
            break

    requested_limit = max(0, column_limit - len(columns))
    requested = set(variables)

    for monitor_index, monitor in enumerate(
        result_file.GetContents("*.IntMon", 1) or []
    ):
        if time.monotonic() >= deadline:
            raise TimeoutError("Result metadata time budget exceeded")
        try:
            selected = {
                monitor.GetVar(index)
                for index in range(int(monitor.NVars()))
            }
            selected.intersection_update(requested)
            if not selected:
                continue

            target = monitor.GetAttribute("obj_id")
            if target is not None:
                targets = [target]
            else:
                class_name = monitor.GetAttribute("className")
                if not isinstance(class_name, str) or not class_name.strip():
                    raise ValueError("selection has no object target or className")
                targets = app.GetCalcRelevantObjects(
                    f"*.{class_name.strip()}"
                ) or []

            for target in targets:
                for variable in selected:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Result metadata time budget exceeded")
                    column = result_file.FindColumn(target, variable)
                    if not isinstance(column, int) or not 0 <= column < total_columns:
                        continue
                    columns.setdefault(column, {
                        "index": column,
                        "variable": variable,
                        "object": _object_summary(target),
                    })
                    requested_count = sum(
                        item["variable"] != "b:i_obj"
                        for item in columns.values()
                    )
                    if requested_count > requested_limit:
                        ordered = sorted(columns.values(), key=lambda item: item["index"])
                        retained = []
                        kept_requested = 0
                        for item in ordered:
                            if item["variable"] == "b:i_obj":
                                retained.append(item)
                            elif kept_requested < requested_limit:
                                retained.append(item)
                                kept_requested += 1
                        return retained, len(columns), False, errors
        except TimeoutError:
            raise
        except Exception as exc:
            errors.append({
                "monitor_index": monitor_index,
                "message": f"Could not inspect result selection: {exc}",
            })

    ordered = sorted(columns.values(), key=lambda item: item["index"])
    return ordered, len(ordered), True, errors


def _contingency_screening_settings(command):
    """Return the supported ComSimoutage screening settings."""
    def optional_bool(attribute):
        value = _attribute(command, attribute)
        return None if value is None else bool(value)

    method = _attribute(command, "screeningMeth")
    return {
        "screening_method": {0: "dc", 1: "ac_linearised"}.get(
            method, "unknown" if method is None else f"unknown:{method}"
        ),
        "simple_loading_criterion": optional_bool("scrCritSimple"),
        "simple_loading_threshold_pct": _attribute(command, "maxLoadAbs"),
        "combined_loading_criterion": optional_bool("scrCritComb"),
        "combined_loading_threshold_pct": _attribute(command, "maxLoad"),
        "relative_loading_change_pct": _attribute(command, "diffLoadBase"),
        "ignore_base_case_overloads": optional_bool("iIgnCriticalBC"),
        "screen_only_recorded_elements": optional_bool("screenRecOnly"),
    }


def _contingency_variable_names(variables):
    """Validate and de-duplicate a result-variable list."""
    if not isinstance(variables, list):
        return [], "variables must be a list of non-empty strings"
    invalid = [
        index for index, variable in enumerate(variables)
        if not isinstance(variable, str) or not variable.strip()
    ]
    if invalid:
        indexes = ", ".join(str(index) for index in invalid)
        return [], (
            "variables entries at indexes " + indexes
            + " must be non-empty strings"
        )
    return list(dict.fromkeys(variable.strip() for variable in variables)), ""


def _contingency_monitor_index(result_file):
    """Read each IntMon once; retain healthy selections and report failures once."""
    indexed, classes, errors = {}, {}, []
    for index, monitor in enumerate(result_file.GetContents("*.IntMon", 1) or []):
        full_name = None
        try:
            obj = monitor.GetAttribute("obj_id")
            if obj is not None:
                full_name = obj.GetFullName()
            variables = {monitor.GetVar(i) for i in range(int(monitor.NVars()))}
            if obj is None:
                if not variables:
                    continue
                class_name = monitor.GetAttribute("className")
                if isinstance(class_name, str) and class_name.strip():
                    classes.setdefault(class_name.strip(), set()).update(variables)
                    continue
                raise RuntimeError(
                    "Selection has no object target or readable className; "
                    "unidentified class/group selections are unsupported. "
                    "Inspect this IntMon in PowerFactory before "
                    "changing recording; it has been left unchanged."
                )
            indexed.setdefault(full_name, []).append((monitor, variables))
        except Exception as exc:
            errors.append({
                "monitor_index": index,
                "object_full_name": full_name,
                "message": f"Could not inspect result selection: {exc}",
            })
    return indexed, classes, errors


def _contingency_recording_request(object_query, variables, calculation_method, max_objects):
    """Validate the common add/remove recording arguments."""
    method = str(calculation_method or "").strip().lower()
    if method not in {"ac", "dc"}:
        raise ValueError("calculation_method must be 'ac' or 'dc'")
    query = str(object_query or "").strip()
    names, error = _contingency_variable_names(variables)
    if error:
        raise ValueError(error)
    if not query or not names:
        raise ValueError("object_query and at least one variable are required")
    try:
        limit = max(1, min(int(max_objects), 1000))
    except (TypeError, ValueError):
        raise ValueError("max_objects must be an integer") from None
    return method, query, names, limit


def _contingency_recording_context(app, method, query):
    """Resolve the active result selection and requested objects for either tool."""
    if app.GetActiveStudyCase() is None:
        raise ValueError("No PowerFactory study case is active")
    command = _existing_contingency_command(app)
    if command is None:
        raise ValueError("ComSimoutage is unavailable")
    result_file = command.GetAttribute("p_rescnt" if method == "ac" else "p_rescntDC")
    if result_file is None:
        raise ValueError(f"{method.upper()} contingency result file is not configured")
    objects = app.GetCalcRelevantObjects(query) or []
    if not objects:
        raise ValueError(f"No objects found for query: {query}")
    return result_file, _object_summary(result_file), objects


def _decode_cell(raw):
    """Decode PowerFactory's ``(status, value)`` result-cell convention."""
    # Older PowerFactory builds can return a bare scalar instead of a pair.
    if (
        isinstance(raw, (list, tuple))
        and len(raw) == 2
        and isinstance(raw[0], int)
    ):
        return raw[0], raw[1]
    return 0, raw


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def ping() -> str:
    """Returns pong. Use this to verify the MCP server is reachable."""
    return "pong"


@mcp.tool()
def close_digsilent() -> str:
    """
    Close the DIgSILENT PowerFactory API session.

    This calls DIgSILENTAgent.close(), which executes app.Exit() and clears
    shared handles in the current Python process.

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    _, DIgSILENTAgent = _load_modules()

    def _impl():
        DIgSILENTAgent.close()
        return {"success": True, "message": "DIgSILENT API closed"}

    return _to_json(_pf(_impl))


@mcp.tool()
def get_config(cfg_path: str = "") -> str:
    """Return the active simulation_config.json as a JSON string."""
    path = checked_path(cfg_path, purpose="cfg_path") if cfg_path else _default_cfg_path()
    with open(path, "r", encoding="utf-8") as fh:
        return json.dumps(json.load(fh), indent=2, ensure_ascii=False)

@mcp.tool()
def get_active_project() -> str:
    """Return the currently active PowerFactory project."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        project = app.GetActiveProject()
        if project is None:
            return {
                "success": False,
                "message": "No PowerFactory project is active",
            }
        return {
            "success": True,
            "name": project.GetAttribute("loc_name"),
            "full_name": project.GetFullName(),
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def get_active_study_case() -> str:
    """Return the currently active PowerFactory study case."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        study_case = app.GetActiveStudyCase()
        if study_case is None:
            return {
                "success": False,
                "message": "No PowerFactory study case is active",
            }
        return {
            "success": True,
            "name": study_case.GetAttribute("loc_name"),
            "full_name": study_case.GetFullName(),
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def get_parameters(
    object_query: str,
    variables: list[str],
    max_results: int = 100,
) -> str:
    """Return selected attributes for calculation-relevant objects."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        variable_names = list(
            dict.fromkeys(name.strip() for name in variables if name.strip())
        )
        if not variable_names:
            return {
                "success": False,
                "message": "At least one variable is required",
            }

        objects = app.GetCalcRelevantObjects(object_query) or []
        if not objects:
            return {
                "success": False,
                "message": f"No objects found for query: {object_query}",
            }

        limit = max(1, min(int(max_results), 1000))
        results = []

        for obj in objects[:limit]:
            values = {}
            errors = {}

            for variable in variable_names:
                try:
                    value = obj.GetAttribute(variable)
                    if not isinstance(
                        value,
                        (str, int, float, bool, list, type(None)),
                    ):
                        value = str(value)
                    values[variable] = value
                except Exception as exc:
                    errors[variable] = str(exc)

            item = {
                "name": obj.GetAttribute("loc_name"),
                "class_name": obj.GetClassName(),
                "full_name": obj.GetFullName(),
                "values": values,
            }
            if errors:
                item["errors"] = errors

            results.append(item)

        return {
            "success": True,
            "query": object_query,
            "variables": variable_names,
            "total_count": len(objects),
            "returned_count": len(results),
            "results": results,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

_COMPONENT_QUERIES = {
    "buses": ("*.ElmTerm",),
    "lines": ("*.ElmLne",),
    "branches": (
        "*.ElmLne",
        "*.ElmTr2",
        "*.ElmTr3",
        "*.ElmCoup",
    ),
    "transformers": (
        "*.ElmTr2",
        "*.ElmTr3",
    ),
    "loads": (
        "*.ElmLod",
        "*.ElmLodmv",
        "*.ElmLodlv",
        "*.ElmLodlvp",
    ),
    "generators": (
        "*.ElmSym",
        "*.ElmGenstat",
        "*.ElmPvsys",
    ),
    "synchronous_generators": ("*.ElmSym",),
    "static_generators": ("*.ElmGenstat",),
    "pv_systems": ("*.ElmPvsys",),
    "storage": ("*.ElmBattery",),
    "external_grids": ("*.ElmXnet",),
    "switches": ("*.ElmCoup",),
}
_COMPONENT_CLASSES = {
    query.rsplit(".", 1)[-1]
    for queries in _COMPONENT_QUERIES.values()
    for query in queries
}

@mcp.tool()
def list_objects(object_query: str = "*.ElmTerm", max_results: int = 100) -> str:
    """List calculation-relevant PowerFactory objects."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        objects = app.GetCalcRelevantObjects(object_query) or []
        limit = max(1, min(int(max_results), 1000))
        results = [
            {
                "name": obj.GetAttribute("loc_name"),
                "class_name": obj.GetClassName(),
                "full_name": obj.GetFullName(),
            }
            for obj in objects[:limit]
        ]
        return {
            "success": True,
            "query": object_query,
            "total_count": len(objects),
            "returned_count": len(results),
            "results": results,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def list_components(
    component_type: str = "all",
    max_results: int = 100,
) -> str:
    """List components using a friendly equipment category."""
    category = (
        component_type.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    if category == "all":
        queries = ("*.Elm*",)
    else:
        queries = _COMPONENT_QUERIES.get(category)

    if queries is None:
        return _to_json({
            "success": False,
            "message": f"Unsupported component type: {component_type}",
            "supported_component_types": [
                "all",
                *_COMPONENT_QUERIES,
            ],
        })

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        components = {}

        for query in queries:
            for obj in app.GetCalcRelevantObjects(query) or []:
                if (
                    category == "all"
                    and obj.GetClassName() not in _COMPONENT_CLASSES
                ):
                    continue
                full_name = obj.GetFullName()
                components.setdefault(full_name, obj)

        limit = max(1, min(int(max_results), 1000))
        results = []
        for full_name, obj in list(components.items())[:limit]:
            try:
                out_of_service = bool(obj.GetAttribute("outserv"))
            except Exception:
                out_of_service = None

            results.append({
                    "name": obj.GetAttribute("loc_name"),
                    "class_name": obj.GetClassName(),
                    "full_name": full_name,
                    "out_of_service": out_of_service,
            })

        return {
            "success": True,
            "component_type": category,
            "queries": list(queries),
            "total_count": len(components),
            "returned_count": len(results),
            "results": results,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def list_study_cases(max_results: int = 100) -> str:
    """List the study cases in the active PowerFactory project."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        folder = app.GetProjectFolder("study")
        if folder is None:
            return {
                "success": False,
                "message": "Study-case folder was not found",
            }
        study_cases = folder.GetContents("*.IntCase", 1) or []
        active_case = app.GetActiveStudyCase()
        active_full_name = active_case.GetFullName() if active_case else None
        limit = max(1, min(int(max_results), 1000))

        results = []

        for study_case in study_cases[:limit]:
            full_name = study_case.GetFullName()
            results.append({
                "name": study_case.GetAttribute("loc_name"),
                "full_name": full_name,
                "is_active": full_name == active_full_name,
            })
        return {
            "success": True,
            "total_count": len(study_cases),
            "returned_count": len(results),
            "results": results,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def list_contingencies(max_results: int = 100) -> str:
    """List fault-library cases, including EvtShc faults, without creating commands."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        project = app.GetActiveProject()
        if project is None:
            return {
                "success": False,
                "message": "No PowerFactory project is active",
            }

        def event_summary(event, action_attribute):
            return {
                "name": _attribute(event, "loc_name"),
                "class_name": event.GetClassName(),
                "target": _object_summary(_attribute(event, "p_target")),
                "time_s": _attribute(event, "time"),
                "action": _attribute(event, action_attribute),
                "disabled": bool(_attribute(event, "outserv", 0)),
            }

        fault_cases = []
        for fault_case in project.GetContents("*.IntEvt", 1) or []:
            parent = fault_case.GetParent()
            if parent is None or parent.GetClassName() != "IntFltcases":
                continue
            outages = fault_case.GetContents("*.EvtOutage", 1) or []
            switches = fault_case.GetContents("*.EvtSwitch", 1) or []
            faults = fault_case.GetContents("*.EvtShc", 1) or []
            fault_cases.append((fault_case, outages, switches, faults))

        fault_cases.sort(key=lambda entry: not (entry[1] or entry[2] or entry[3]))
        limit = max(1, min(int(max_results), 1000))
        results = []
        for fault_case, outages, switches, faults in fault_cases[:limit]:
            results.append({
                **_object_summary(fault_case),
                "event_count": len(outages) + len(switches) + len(faults),
                "fault_count": len(faults),
                "faults": [
                    {
                        **event_summary(fault, "i_shc"),
                        "fault_position_pct": _attribute(fault, "shcLocation"),
                    }
                    for fault in faults
                ],
                "outage_count": len(outages),
                "outages": [
                    event_summary(outage, "i_what")
                    for outage in outages
                ],
                "switch_count": len(switches),
                "switches": [
                    event_summary(switch, "i_switch")
                    for switch in switches
                ],
            })

        return {
            "success": True,
            "total_count": len(fault_cases),
            "returned_count": len(results),
            "results": results,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def get_contingency_configuration() -> str:
    """Read the active Contingency Analysis command without executing it."""
    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        if app.GetActiveStudyCase() is None:
            return {
                "success": False,
                "message": "No PowerFactory study case is active",
            }

        command = _existing_contingency_command(app)
        if command is None:
            return {
                "success": False,
                "message": "ComSimoutage is unavailable",
            }

        return {
            "success": True,
            "command": _object_summary(command),
            "settings": {
                "data_source": _attribute(command, "dat_src"),
                "calculation_method": _attribute(command, "iopt_method"),
                "linear_method": _attribute(command, "iopt_Linear"),
                "linear_option": _attribute(command, "copt_Linear"),
                "combine_ac_dc": _attribute(command, "iACDCCombine"),
                "dynamic_contingencies": _attribute(command, "dynamicCase"),
                **_contingency_screening_settings(command),
            },
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def configure_contingency_screening(
    screening_method: str = "",
    simple_loading_criterion: bool | None = None,
    simple_loading_threshold_pct: float | None = None,
    combined_loading_criterion: bool | None = None,
    combined_loading_threshold_pct: float | None = None,
    relative_loading_change_pct: float | None = None,
    ignore_base_case_overloads: bool | None = None,
    screen_only_recorded_elements: bool | None = None,
) -> str:
    """Configure persistent screening settings in the active study case.

    No calculation is executed. Changes persist after this call; original
    values are restored if a write fails. ``screening_method='dc'`` selects
    DC load-flow screening; ``'ac_linearised'`` selects linearised AC screening.
    An empty method string leaves that setting unchanged; ``None`` leaves
    each other argument unchanged.

    ``simple_loading_criterion`` enables recalculation when loading exceeds
    ``simple_loading_threshold_pct`` (percentage of rated loading).
    ``combined_loading_criterion`` enables the combined test: loading exceeds
    ``combined_loading_threshold_pct`` AND its relative change from the base
    case exceeds ``relative_loading_change_pct``. All thresholds are finite,
    non-negative percentages, not fractions.
    ``ignore_base_case_overloads`` excludes components overloaded in the base
    case; ``screen_only_recorded_elements`` restricts screening to elements
    included in result recording. Supply at least one setting to update.
    """
    method_name = str(screening_method or "").strip().casefold()
    methods = {"dc": 0, "ac_linearised": 1}
    if method_name and method_name not in methods:
        return _to_json({
            "success": False,
            "message": "screening_method must be 'dc' or 'ac_linearised'",
        })

    parsed = {}
    try:
        for name, value in (
            ("simple_loading_threshold_pct", simple_loading_threshold_pct),
            ("combined_loading_threshold_pct", combined_loading_threshold_pct),
            ("relative_loading_change_pct", relative_loading_change_pct),
        ):
            if value is None:
                continue
            number = float(value)
            if not math.isfinite(number) or number < 0:
                raise ValueError(f"{name} must be finite and non-negative")
            parsed[name] = number
    except (TypeError, ValueError) as exc:
        return _to_json({"success": False, "message": str(exc)})

    updates = {}
    if method_name:
        updates["screeningMeth"] = methods[method_name]
    for value, attribute in (
        (simple_loading_criterion, "scrCritSimple"),
        (combined_loading_criterion, "scrCritComb"),
        (ignore_base_case_overloads, "iIgnCriticalBC"),
        (screen_only_recorded_elements, "screenRecOnly"),
    ):
        if value is not None:
            updates[attribute] = int(value)
    for name, attribute in (
        ("simple_loading_threshold_pct", "maxLoadAbs"),
        ("combined_loading_threshold_pct", "maxLoad"),
        ("relative_loading_change_pct", "diffLoadBase"),
    ):
        if name in parsed:
            updates[attribute] = parsed[name]

    if not updates:
        return _to_json({
            "success": False,
            "message": "At least one screening setting must be provided",
        })

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        if app.GetActiveStudyCase() is None:
            return {
                "success": False,
                "message": "No PowerFactory study case is active",
            }
        command = _existing_contingency_command(app)
        if command is None:
            return {"success": False, "message": "ComSimoutage is unavailable"}

        previous = {
            attribute: command.GetAttribute(attribute)
            for attribute in updates
        }
        before = _contingency_screening_settings(command)
        try:
            for attribute, expected in updates.items():
                command.SetAttribute(attribute, expected)
                actual = command.GetAttribute(attribute)
                matches = (
                    int(actual) == expected
                    if isinstance(expected, int)
                    else math.isclose(float(actual), expected, abs_tol=1e-6)
                )
                if not matches:
                    raise RuntimeError(
                        f"PowerFactory did not retain {attribute}={expected}"
                    )
        except Exception as exc:
            rollback_errors = []
            for attribute, value in previous.items():
                try:
                    command.SetAttribute(attribute, value)
                except Exception as rollback_exc:
                    rollback_errors.append(f"{attribute}: {rollback_exc}")
            message = f"Could not configure contingency screening: {exc}"
            if rollback_errors:
                message += "; rollback failed for " + ", ".join(rollback_errors)
            return {"success": False, "message": message}

        after = _contingency_screening_settings(command)
        return {
            "success": True,
            "message": (
                "Contingency screening configuration updated"
                if before != after
                else "Contingency screening configuration already matched"
            ),
            "command": _object_summary(command),
            "changed": before != after,
            "before": before,
            "settings": after,
        }

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))

@mcp.tool()
def import_project(
    file_path: str = "",
    open_digsilent: bool = True,
) -> str:
    """
    Import a DIgSILENT PowerFactory project from a .pfd file and activate it.

    PowerFactory must be running before calling this tool. After a successful
    import the project is immediately active and ready for simulation.

    Parameters
    ----------
    file_path : str
        Absolute path to the .pfd export file.
        No default is bundled. Provide the project export path at call time.
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    if not file_path:
        return json.dumps({"success": False, "message": "file_path is required"})
    file_path = checked_path(file_path, purpose="file_path")
    return _agent_result("import_project", file_path, open_digsilent)


@mcp.tool()
def create_study_case(
    case_name: str,
    base_study_case: str = "0. Base",
    open_digsilent: bool = True,
    request_id: str = "",
    cfg_path: str = "",
) -> str:
    """
    Create and activate a study case without running RMS simulation.

    Parameters
    ----------
    case_name : str
        Name of the target study case to create/activate.
    base_study_case : str
        Name of the source study case used when case_name does not exist.
        Default: "0. Base".
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().
    request_id : str
        Optional idempotency key. If repeated, the server returns the
        cached result and does not execute the action again.
    cfg_path : str, optional
        Path to simulation_config.json used to read project_path.

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    SimulationConfig, _ = _load_modules()
    path = checked_path(cfg_path, purpose="cfg_path") if cfg_path else _default_cfg_path()
    cfg = SimulationConfig.from_json(path)
    return _agent_result(
        "create_study_case",
        cfg.project_path,
        case_name,
        base_study_case,
        open_digsilent,
        request_id,
    )


@mcp.tool()
def modify_parameter(
    object_name: str,
    variable: str,
    new_value: Any,
    open_digsilent: bool = True,
) -> str:
    """
    Modify a PowerFactory attribute for all objects matching object_name.

    Parameters
    ----------
    object_name : str
        Query passed to app.GetCalcRelevantObjects
        (example: "G 10.ElmSym").
    variable : str
        Attribute name to update (example: "e:outserv").
    new_value : Any
        New value to write with SetAttribute.
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    return _agent_result(
        "modify_parameter",
        object_name,
        variable,
        new_value,
        open_digsilent,
    )


@mcp.tool()
def add_component(
    component_type: str,
    component_name: str,
    parameters: dict[str, Any],
    grid_name: str = "",
    out_of_service: bool = False,
    open_digsilent: bool = True,
    update_graphics: bool = False,
) -> str:
    """
    Create a bus, load, generator, line, or transformer.

    Required parameters by component type:
    - bus: nominal_voltage_kv
    - load: bus_name, active_power_mw; optional reactive_power_mvar
    - generator: bus_name, template_generator, active_power_mw;
      optional reactive_power_mvar
    - line: bus1_name, bus2_name, template_line, length_km
    - transformer: high_voltage_bus_name, low_voltage_bus_name,
      template_transformer

    Connected loads, generators, lines, and transformers receive one closed
    circuit breaker in each generated cubicle.

    Set update_graphics to true to insert missing network elements into
    the currently active single-line diagram using PowerFactory's Diagram
    Layout Tool. If insertion fails, the network component remains created,
    but the tool returns success=false with the graphical error.
    """
    return _agent_result(
        "add_component",
        component_type,
        component_name,
        parameters,
        grid_name,
        out_of_service,
        open_digsilent,
        update_graphics,
    )


@mcp.tool()
def delete_component(
    component_type: str,
    component_name: str,
    grid_name: str = "",
    confirmation: str = "",
    open_digsilent: bool = True,
    update_graphics: bool = False,
) -> str:
    """
    Preview or delete one exactly named grid component.

    Call without confirmation first. To perform deletion, repeat the call
    using the exact confirmation token returned by the preview.

    Set update_graphics to true for confirmed deletion from every single-line
    diagram in the active project. Preview calls do not modify any diagram.
    A cleanup failure can return success=false with deleted=true when the
    network component is gone but graphical or cubicle cleanup is incomplete.
    """
    return _agent_result(
        "delete_component",
        component_type,
        component_name,
        grid_name,
        confirmation,
        open_digsilent,
        update_graphics,
        structured=True,
    )


@mcp.tool()
def run_loadflow(
    open_digsilent: bool = True,
    save_csv: bool = False,
    cfg_path: str = "",
) -> str:
    """
    Run a load flow calculation (ComLdf) on the currently active study case.

    Parameters
    ----------
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().
    save_csv : bool
        If True, also exports a load-flow snapshot CSV with:
        - buses (*.ElmTerm): m:u, m:phiu
        - generators (*.ElmSym): m:P:bus1, m:Q:bus1
        - loads (*.ElmLod): e:plini, e:qlini
        Default: False.
    cfg_path : str, optional
        Optional path to simulation_config.json used for output_dir/run_label
        when save_csv=True. Defaults to this server's config file.

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    SimulationConfig, DIgSILENTAgent = _load_modules()

    output_dir = r"C:\RMS_Results"
    run_label = "run_001"
    if save_csv:
        path = checked_path(cfg_path, purpose="cfg_path") if cfg_path else _default_cfg_path()
        try:
            cfg = SimulationConfig.from_json(path)
            output_dir = getattr(cfg, "output_dir", output_dir) or output_dir
            output_dir = _ensure_checked_directory(
                output_dir, purpose="configured output directory"
            )
            run_label = getattr(cfg, "run_label", run_label) or run_label
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "message": f"Could not read config for CSV export: {e}",
                }
            )

    return _agent_result(
        "load_flow",
        open_digsilent,
        save_csv,
        output_dir,
        run_label,
    )


@mcp.tool()
def run_short_circuit(open_digsilent: bool = True) -> str:
    """
    Run a short-circuit calculation (ComShc) on the currently active study case.

    Parameters
    ----------
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    return _agent_result("short_circuit", open_digsilent)


@mcp.tool()
def create_contingency(
    case_name: str,
    target_query: str,
    action: str = "open",
    time_s: float = 0.0,
    event_name: str = "Switch Event",
    folder_name: str = "Fault Cases",
    open_digsilent: bool = True,
) -> str:
    """Create or reuse one switch-based contingency definition."""
    return _agent_result(
        "create_contingency",
        case_name,
        target_query,
        action,
        time_s,
        event_name,
        folder_name,
        open_digsilent,
        structured=True,
    )


@mcp.tool()
def run_contingency_analysis(
    calculation_method: str = "configured",
    open_digsilent: bool = True,
) -> str:
    """
    Execute the configured Contingency Analysis command (ComSimoutage).

    The tool uses the active study case's existing contingency definitions,
    filters, and result selection. ``calculation_method`` may retain the
    configured mode or explicitly select AC, DC, AC linearised, or linearised
    screening with AC recalculation.

    Parameters
    ----------
    calculation_method : str
        One of ``configured`` (default), ``ac``, ``dc``, ``ac_linearised``,
        or ``linearised_screening``.
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON containing the command identity, selected settings, native
        execution code, and completion status.
    """
    return _agent_result(
        "run_contingency_analysis",
        open_digsilent,
        calculation_method,
        structured=True,
    )


@mcp.tool()
def get_contingency_results(
    calculation_method: str = "ac",
    max_rows: int = 100,
    max_columns: int = 100,
    variables: list[str] | None = None,
    max_read_seconds: float = 5.0,
) -> str:
    """Read a bounded rectangular slice of a contingency result file.

    ``calculation_method`` selects the configured AC or DC ``ElmRes`` object.
    The result is deliberately bounded because contingency files are sparse
    and can contain hundreds of columns even for a single fault case.
    ``variables`` filters exact identifiers (e.g. ["c:loading"]); None reads
    all identifiers. Column indexes remain original file indexes. Sparse holes
    become null without per-cell API calls. ``max_read_seconds`` (0 < value <=
    30) is a cooperative budget, not an interrupt of a blocked native call.
    Filtered metadata is resolved from ``IntMon`` selections and ``FindColumn``
    rather than scanning every result column. No command is created. A
    transient ``IntVec`` is deleted after bulk reads; sparse iterators are the
    fallback. Object metadata may be null for non-element columns. Reading does
    not run or refresh the analysis.
    """
    method = calculation_method.strip().lower()
    if method not in {"ac", "dc"}:
        return _to_json({
            "success": False,
            "message": "calculation_method must be 'ac' or 'dc'",
        })

    try:
        row_limit = int(max_rows)
        column_limit = int(max_columns)
    except (TypeError, ValueError):
        return _to_json({
            "success": False,
            "message": "max_rows and max_columns must be integers",
        })
    if row_limit < 1 or column_limit < 1:
        return _to_json({
            "success": False,
            "message": "max_rows and max_columns must be positive",
        })
    if row_limit * column_limit > 20_000:
        return _to_json({
            "success": False,
            "message": "Requested result slice exceeds 20,000 cells",
        })

    try:
        if variables is None:
            variable_filter = None
        else:
            variable_names, variable_error = _contingency_variable_names(variables)
            if variable_error:
                raise ValueError(variable_error)
            if not variable_names:
                raise ValueError("variables must contain at least one variable name")
            variable_filter = set(variable_names)
        read_seconds = float(max_read_seconds)
        if not math.isfinite(read_seconds) or not 0 < read_seconds <= 30:
            raise ValueError("max_read_seconds must be finite, positive, and at most 30")
    except (TypeError, ValueError) as exc:
        return _to_json({"success": False, "message": str(exc)})

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        if app.GetActiveStudyCase() is None:
            return {
                "success": False,
                "message": "No PowerFactory study case is active",
            }

        command = _existing_contingency_command(app)
        if command is None:
            return {
                "success": False,
                "message": "ComSimoutage is unavailable",
            }

        reference_name = "p_rescnt" if method == "ac" else "p_rescntDC"
        result_file = command.GetAttribute(reference_name)
        if result_file is None:
            return {
                "success": False,
                "message": f"{method.upper()} contingency result file is not configured",
            }

        load_code = result_file.Load()
        if load_code not in (0, None):
            return {
                "success": False,
                "message": f"ElmRes.Load returned error code {load_code}",
            }

        try:
            deadline = time.monotonic() + read_seconds
            total_rows = result_file.GetNumberOfRows()
            total_columns = result_file.GetNumberOfColumns()
            returned_rows = min(total_rows, row_limit)
            metadata_errors = []
            if variable_filter is not None:
                (
                    columns,
                    matching_columns,
                    matching_columns_complete,
                    metadata_errors,
                ) = _filtered_result_columns(
                    app,
                    result_file,
                    total_columns,
                    variable_filter,
                    column_limit,
                    deadline,
                )
            else:
                columns = []
                for column in range(min(total_columns, column_limit)):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Result metadata time budget exceeded; "
                            "request fewer columns"
                        )
                    variable = result_file.GetVariable(column)
                    item = {
                        "index": column,
                        "variable": variable,
                        "object": None,
                    }
                    result_object = result_file.GetObject(column)
                    if result_object is not None:
                        item["object"] = _object_summary(result_object)
                    columns.append(item)
                matching_columns = total_columns
                matching_columns_complete = True
            returned_columns = len(columns)
            object_column = next(
                (
                    position
                    for position, column in enumerate(columns)
                    if column["variable"] == "b:i_obj"
                ),
                None,
            )

            rows = []
            cell_rows = _result_cells(app, result_file, returned_rows,
                                      [column["index"] for column in columns], deadline)
            for row, cells in enumerate(cell_rows):
                values = []
                errors = []
                for column in columns:
                    index = column["index"]
                    error_code, value = cells.get(index, (0, None))

                    values.append(value if error_code == 0 else None)
                    if error_code != 0:
                        errors.append({
                            "column": index,
                            "code": error_code,
                        })

                item = {"index": row, "values": values}
                if object_column is not None and values[object_column] is not None:
                    object_index = int(values[object_column])
                    item["object_index"] = object_index
                    object_error, result_object = _decode_cell(
                        result_file.GetObj(object_index)
                    )
                    if object_error == 0 and result_object is not None:
                        item["object"] = _object_summary(result_object)
                    elif object_error != 0:
                        item["object_error_code"] = object_error
                if errors:
                    item["errors"] = errors
                rows.append(item)

            return {
                "success": True,
                "calculation_method": method,
                "result_file": _object_summary(result_file),
                "total_rows": total_rows,
                "total_columns": total_columns,
                "matching_columns": matching_columns,
                "matching_columns_complete": matching_columns_complete,
                "returned_rows": returned_rows,
                "returned_columns": returned_columns,
                "truncated": (
                    returned_rows < total_rows
                    or returned_columns < matching_columns
                ),
                "columns": columns,
                "rows": rows,
                **({"metadata_errors": metadata_errors} if metadata_errors else {}),
            }
        finally:
            result_file.Release()

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def add_contingency_result_variables(
    object_query: str,
    variables: list[str],
    calculation_method: str = "ac",
    max_objects: int = 100,
) -> str:
    """Add variables to the configured AC or DC contingency result file.

    This updates the existing ``ElmRes`` recording selection but does not run
    the contingency analysis. Each entry in ``results`` lists the variables
    ``added`` by this call and those ``already_recorded``; ``added_variables``
    and ``already_recorded_variables`` total them. Rerun the analysis only
    when ``added_variables`` is non-zero -- a repeat call adds nothing.
    Class-level selections count as recorded for objects of that class.
    Unreadable or unidentified targetless selections are reported once;
    additions with uncertain recording state are skipped and reported failed.

    Every recorded ``m:u`` / ``c:loading`` column is scanned by
    ``get_contingency_summary``, which refuses files above 20,000 cells
    (rows x columns), so recording those for many objects can disable it.
    """
    try:
        method, query, variable_names, object_limit = _contingency_recording_request(
            object_query, variables, calculation_method, max_objects,
        )
    except (TypeError, ValueError) as exc:
        return _to_json({"success": False, "message": str(exc)})

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        try:
            result_file, result_summary, objects = _contingency_recording_context(
                app, method, query,
            )
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        indexed, classes, errors = _contingency_monitor_index(result_file)
        uncertain = {error["object_full_name"] for error in errors}
        configured = []
        for object_index, obj in enumerate(objects[:object_limit]):
            # Identify the object before writing to it. Anything raised here
            # or below stays scoped to this object, so the record of columns
            # already added survives instead of the whole call surfacing as a
            # failed read.
            try:
                summary = _object_summary(obj)
            except Exception as exc:
                errors.append({
                    "object_index": object_index,
                    "message": f"Could not identify object: {exc}",
                })
                continue
            added = []
            already_recorded = []
            failed = []
            recorded = set().union(*(
                names for _monitor, names in indexed.get(summary["full_name"], [])
            ))
            recorded.update(classes.get(summary["class_name"], set()))
            for variable in variable_names:
                if variable in recorded:
                    already_recorded.append(variable)
                    continue
                if None in uncertain or summary["full_name"] in uncertain:
                    failed.append(variable)
                    continue
                try:
                    code = result_file.AddVariable(obj, variable)
                except Exception as exc:
                    errors.append({
                        "object_index": object_index,
                        "object": summary,
                        "variable": variable,
                        "message": str(exc),
                    })
                    failed.append(variable)
                    continue
                if code not in (0, None):
                    errors.append({
                        "object_index": object_index,
                        "object": summary,
                        "variable": variable,
                        "code": code,
                    })
                    failed.append(variable)
                    continue
                added.append(variable)
            configured.append({
                "object": summary,
                "variables": [
                    variable for variable in variable_names
                    if variable in added or variable in already_recorded
                ],
                "added": added,
                "already_recorded": already_recorded,
                "failed": failed,
            })

        response = {
            "success": not errors,
            "calculation_method": method,
            "result_file": result_summary,
            "query": query,
            "variables": variable_names,
            "total_objects": len(objects),
            "configured_objects": sum(bool(item["variables"]) for item in configured),
            "configured_variables": sum(
                len(item["variables"]) for item in configured
            ),
            "added_variables": sum(len(item["added"]) for item in configured),
            "already_recorded_variables": sum(
                len(item["already_recorded"]) for item in configured
            ),
            "failed_variables": sum(len(item["failed"]) for item in configured),
            "truncated": len(objects) > object_limit,
            "results": configured,
        }
        if response["added_variables"]:
            response["message"] = (
                "Result recording selection updated; rerun contingency analysis "
                "to populate the added variables"
            )
        elif not errors:
            response["message"] = (
                "All requested variables were already recorded; no change"
            )
        else:
            response["message"] = "No result variables were added"
        if errors:
            response["message"] = (
                "Some result variables could not be configured; "
                + response["message"][0].lower()
                + response["message"][1:]
            )
            response["errors"] = errors
        return response

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def remove_contingency_result_variables(
    object_query: str,
    variables: list[str],
    calculation_method: str = "ac",
    max_objects: int = 100,
) -> str:
    """Remove variables from the configured AC or DC result selection.

    The matching ``IntMon`` selections are updated without executing the
    contingency analysis. Rerun it only when ``removed_variables`` is non-zero
    so the result file is rebuilt without those columns.
    ``failed_variables`` is separate from ``already_absent_variables``. If one
    monitor succeeds and another fails, that variable appears in both
    ``removed`` and ``failed`` to retain the partial change. ``configured_objects``
    counts objects with readable matching selections; ``objects_without_selection``
    counts objects with none. Variables recorded by a matching class selection
    cannot be removed for one object: they are reported failed and neither the
    class nor object selections for that variable are changed. Unreadable or
    unidentified selections are reported once; uncertain absence is never claimed.
    """
    try:
        method, query, variable_names, object_limit = _contingency_recording_request(
            object_query, variables, calculation_method, max_objects,
        )
    except (TypeError, ValueError) as exc:
        return _to_json({"success": False, "message": str(exc)})

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        try:
            result_file, result_summary, objects = _contingency_recording_context(
                app, method, query,
            )
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        indexed, classes, errors = _contingency_monitor_index(result_file)
        uncertain = {error["object_full_name"] for error in errors}
        configured = []
        for object_index, obj in enumerate(objects[:object_limit]):
            try:
                summary = _object_summary(obj)
            except Exception as exc:
                errors.append({
                    "object_index": object_index,
                    "message": f"Could not identify object: {exc}",
                })
                continue

            matching_monitors = indexed.get(summary["full_name"], [])
            class_variables = classes.get(summary["class_name"], set())
            selection_unknown = None in uncertain or summary["full_name"] in uncertain
            removed = []
            already_absent = []
            failed = []
            for variable in variable_names:
                if variable in class_variables:
                    failed.append(variable)
                    errors.append({
                        "object_index": object_index,
                        "object": summary,
                        "variable": variable,
                        "message": (
                            f"Variable is recorded by class-level {summary['class_name']} "
                            "selection; object-specific removal cannot exclude this "
                            "object. Class and object selections were left unchanged."
                        ),
                    })
                    continue
                removed_here = False
                failed_here = selection_unknown
                for monitor, _names in matching_monitors:
                    try:
                        code = monitor.RemoveVar(variable)
                    except Exception as exc:
                        errors.append({
                            "object_index": object_index,
                            "object": summary,
                            "variable": variable,
                            "message": str(exc),
                        })
                        failed_here = True
                        continue
                    if code in (0, None):
                        removed_here = True
                    elif code != 1:
                        errors.append({
                            "object_index": object_index,
                            "object": summary,
                            "variable": variable,
                            "code": code,
                        })
                        failed_here = True
                if removed_here:
                    removed.append(variable)
                if failed_here:
                    failed.append(variable)
                elif not removed_here:
                    already_absent.append(variable)

            configured.append({
                "object": summary,
                "variables": variable_names,
                "removed": removed,
                "already_absent": already_absent,
                "failed": failed,
                "has_selection": bool(matching_monitors or class_variables),
                "selection_unknown": selection_unknown,
            })

        response = {
            "success": not errors,
            "calculation_method": method,
            "result_file": result_summary,
            "query": query,
            "variables": variable_names,
            "total_objects": len(objects),
            "configured_objects": sum(item["has_selection"] for item in configured),
            "objects_without_selection": sum(
                not item["has_selection"] and not item["selection_unknown"]
                for item in configured
            ),
            "removed_variables": sum(
                len(item["removed"]) for item in configured
            ),
            "already_absent_variables": sum(
                len(item["already_absent"]) for item in configured
            ),
            "failed_variables": sum(len(item["failed"]) for item in configured),
            "truncated": len(objects) > object_limit,
            "results": configured,
        }
        if response["removed_variables"]:
            response["message"] = (
                "Result recording selection updated; rerun contingency analysis "
                "to rebuild the result file"
            )
        elif not errors:
            response["message"] = (
                "All requested variables were already absent; no change"
            )
        else:
            response["message"] = "No result variables were removed"
        if errors:
            response["message"] = (
                "Some result variables could not be removed; "
                + response["message"][0].lower()
                + response["message"][1:]
            )
            response["errors"] = errors
        return response

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def get_contingency_summary(
    calculation_method: str = "ac",
    min_voltage_pu: float = 0.9,
    max_voltage_pu: float = 1.1,
    max_loading_pct: float = 100.0,
    max_results: int = 100,
    max_affected_elements: int = 100,
) -> str:
    """Summarize bounded existing contingency results without running a calculation."""
    method = str(calculation_method or "").strip().lower()
    if method not in {"ac", "dc"}:
        return _to_json({
            "success": False,
            "message": "calculation_method must be 'ac' or 'dc'",
        })

    try:
        minimum_voltage = float(min_voltage_pu)
        maximum_voltage = float(max_voltage_pu)
        maximum_loading = float(max_loading_pct)
        result_limit = max(1, min(int(max_results), 1000))
        affected_limit = max(1, min(int(max_affected_elements), 1000))
    except (TypeError, ValueError):
        return _to_json({
            "success": False,
            "message": (
                "Thresholds must be numbers and result limits must be integers"
            ),
        })
    if (
        not all(math.isfinite(value) for value in (
            minimum_voltage,
            maximum_voltage,
            maximum_loading,
        ))
        or minimum_voltage >= maximum_voltage
        or maximum_loading < 0
    ):
        return _to_json({
            "success": False,
            "message": "Voltage limits must increase and max_loading_pct must be non-negative",
        })

    _, DIgSILENTAgent = _load_modules()

    def _impl(app):
        if app.GetActiveStudyCase() is None:
            return {
                "success": False,
                "message": "No PowerFactory study case is active",
            }

        command = _existing_contingency_command(app)
        if command is None:
            return {"success": False, "message": "ComSimoutage is unavailable"}

        reference_name = "p_rescnt" if method == "ac" else "p_rescntDC"
        result_file = command.GetAttribute(reference_name)
        if result_file is None:
            return {
                "success": False,
                "message": f"{method.upper()} contingency result file is not configured",
            }

        load_code = result_file.Load()
        if load_code not in (0, None):
            return {
                "success": False,
                "message": f"ElmRes.Load returned error code {load_code}",
            }

        def value_at(row, column):
            error_code, value = _decode_cell(
                result_file.GetValue(row, column)
            )
            return value if error_code == 0 else None

        def object_at(index):
            error_code, value = _decode_cell(result_file.GetObj(int(index)))
            return value if error_code == 0 else None

        def affected_elements(contingency):
            elements = []
            # Probe one index past the cap: PowerFactory ends the list with
            # None, so a contingency with exactly the cap's worth of elements
            # is only known to be complete once that extra probe comes back.
            for index in range(_MAX_AFFECTED_ELEMENT_SCAN + 1):
                element = contingency.GetObject(index)
                if element is None:
                    break
                if index == _MAX_AFFECTED_ELEMENT_SCAN:
                    raise RuntimeError(
                        "Affected element scan exceeded the safe limit of "
                        f"{_MAX_AFFECTED_ELEMENT_SCAN}"
                    )
                elements.append(_object_summary(element))
            returned = elements[:affected_limit]
            return {
                "affected_elements": returned,
                "total_affected_elements": len(elements),
                "returned_affected_elements": len(returned),
                "affected_elements_truncated": len(returned) < len(elements),
            }

        def finish(entry):
            voltages = list(entry.pop("_voltages").values())
            loadings = list(entry.pop("_loadings").values())
            entry["voltage_violations"] = [
                value for value in voltages
                if value["voltage_pu"] < minimum_voltage
                or value["voltage_pu"] > maximum_voltage
            ]
            entry["overloads"] = [
                value for value in loadings
                if value["loading_pct"] > maximum_loading
            ]
            entry["minimum_voltage"] = min(
                voltages,
                key=lambda value: value["voltage_pu"],
                default=None,
            )
            entry["maximum_voltage"] = max(
                voltages,
                key=lambda value: value["voltage_pu"],
                default=None,
            )
            entry["maximum_loading"] = max(
                loadings,
                key=lambda value: value["loading_pct"],
                default=None,
            )
            return entry

        try:
            total_rows = result_file.GetNumberOfRows()
            total_columns = result_file.GetNumberOfColumns()
            metadata = {}
            measurements = []
            for column in range(total_columns):
                variable = result_file.GetVariable(column)
                if variable in {"b:i_obj", "b:inoconv"}:
                    metadata[variable] = column
                if variable not in {"m:u", "c:loading"}:
                    continue
                monitored_object = result_file.GetObject(column)
                if monitored_object is not None:
                    measurements.append((column, variable, monitored_object))

            if "b:i_obj" not in metadata:
                return {
                    "success": False,
                    "message": "Result file has no b:i_obj contingency column",
                }
            if total_rows * (len(metadata) + len(measurements)) > 20_000:
                return {
                    "success": False,
                    "message": "Interpreted result scan exceeds 20,000 cells",
                }

            base_case = {
                "converged": None,
                "convergence_code": None,
                "_voltages": {},
                "_loadings": {},
            }
            contingencies = {}
            for row in range(total_rows):
                object_index = value_at(row, metadata["b:i_obj"])
                result_object = (
                    object_at(object_index)
                    if object_index is not None
                    else None
                )
                if (
                    result_object is not None
                    and result_object.GetClassName() == "ComOutage"
                ):
                    key = result_object.GetFullName()
                    if key not in contingencies:
                        contingencies[key] = {
                            "contingency": _object_summary(result_object),
                            **affected_elements(result_object),
                            "converged": None,
                            "convergence_code": None,
                            "_voltages": {},
                            "_loadings": {},
                        }
                    entry = contingencies[key]
                elif result_object is None:
                    entry = base_case
                else:
                    continue

                convergence_column = metadata.get("b:inoconv")
                convergence_code = (
                    value_at(row, convergence_column)
                    if convergence_column is not None
                    else None
                )
                if convergence_code is not None:
                    entry["convergence_code"] = int(convergence_code)
                    entry["converged"] = int(convergence_code) == 0

                for column, variable, monitored_object in measurements:
                    value = value_at(row, column)
                    if value is None:
                        continue
                    summary = _object_summary(monitored_object)
                    key = summary["full_name"]
                    if variable == "m:u":
                        entry["_voltages"][key] = {
                            **summary,
                            "voltage_pu": float(value),
                        }
                    else:
                        entry["_loadings"][key] = {
                            **summary,
                            "loading_pct": float(value),
                        }

            results = [
                finish(entry)
                for entry in list(contingencies.values())[:result_limit]
            ]
            return {
                "success": True,
                "calculation_method": method,
                "result_file": _object_summary(result_file),
                "thresholds": {
                    "min_voltage_pu": minimum_voltage,
                    "max_voltage_pu": maximum_voltage,
                    "max_loading_pct": maximum_loading,
                },
                "base_case": finish(base_case),
                "total_count": len(contingencies),
                "returned_count": len(results),
                "truncated": len(results) < len(contingencies),
                "results": results,
            }
        finally:
            result_file.Release()

    return _to_json(_pf(_read_only_result, DIgSILENTAgent, _impl))


@mcp.tool()
def run_simulation(
    cfg_path: str = "",
    export_pfd: bool = False,
    open_digsilent: bool = True,
) -> str:
    """
    Run the full DIgSILENT PowerFactory RMS simulation pipeline.

    Steps: connect → activate study case → load flow → RMS simulation
           → CSV export → standard plots → optional PFD export.

    All parameters are read from simulation_config.json.

    Parameters
    ----------
    cfg_path : str, optional
        Absolute path to simulation_config.json. Defaults to the file
        next to this server script.
    export_pfd : bool, optional
        If True, a .pfd export is created in output_dir after CSV export.
    open_digsilent : bool, optional
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag, csv_path, optional pfd_path,
        and per-step status.
    """
    SimulationConfig, DIgSILENTAgent = _load_modules()
    path = checked_path(cfg_path, purpose="cfg_path") if cfg_path else _default_cfg_path()
    cfg = SimulationConfig.from_json(path)
    cfg.output_dir = _ensure_checked_directory(
        cfg.output_dir, purpose="configured output directory"
    )
    cfg.export_pfd = 1 if export_pfd else 0
    cfg.open_digsilent = 1 if open_digsilent else 0

    def _impl():
        agent = DIgSILENTAgent(cfg)
        return agent.run_pipeline()

    return _to_json(_pf(_impl))


@mcp.tool()
def run_custom_case(
    fault_type: str,
    fault_element: str,
    t_fault: float,
    t_clear: float,
    t_end: float = 10.0,
    dt_rms: float = 0.01,
    case_name: str = "Custom_Case",
    switch_element: str = "",
    t_switch: float = 0.0,
    switch_state: int = 0,
    create_new_study_case: bool = False,
    export_pfd: bool = False,
    open_digsilent: bool = True,
    cfg_path: str = "",
) -> str:
    """
    Run a single custom fault case with parameters supplied at call-time.

    Network settings (project path, output directory, signals) are read from
    simulation_config.json; only the fault scenario parameters are overridden
    by the arguments provided here.

    Parameters
    ----------
    fault_type : str
        One of: "bus", "line", "gen_switch" (alias: "generator").
    fault_element : str
        Name of the faulted bus or line element in PowerFactory.
    t_fault : float
        Fault inception time in seconds.
    t_clear : float
        Fault clearing time in seconds.
    t_end : float
        Simulation end time in seconds (default 10.0).
    dt_rms : float
        RMS simulation step size in seconds (default 0.01).
    case_name : str
        Label used for output files and sub-folder name.
    switch_element : str
        Circuit-breaker or switch to operate for gen_switch faults.
    t_switch : float
        Time to operate the switch (defaults to t_fault when 0).
    switch_state : int
        Target switch state: 0 = open/trip, 1 = close.
    create_new_study_case : bool
        If True, creates a new timestamped study case on each call.
        If False (default), reuses case_name as the study case name.
    export_pfd : bool
        If True, a .pfd export is created in output_dir after CSV export.
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().
    cfg_path : str, optional
        Absolute path to simulation_config.json for network settings.

    Returns
    -------
    str
        JSON string with pipeline result (same schema as run_simulation).
    """
    SimulationConfig, DIgSILENTAgent = _load_modules()
    path = checked_path(cfg_path, purpose="cfg_path") if cfg_path else _default_cfg_path()
    cfg = SimulationConfig.from_json(path)
    cfg.output_dir = _ensure_checked_directory(
        cfg.output_dir, purpose="configured output directory"
    )
    if create_new_study_case:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        cfg.study_case = f"{case_name}_{ts}"
    else:
        cfg.study_case = case_name

    cfg.fault_type     = fault_type
    cfg.fault_element  = fault_element
    cfg.t_fault        = t_fault
    cfg.t_clear        = t_clear
    cfg.t_end          = t_end
    cfg.dt_rms         = dt_rms
    cfg.run_label      = case_name
    cfg.switch_element = switch_element
    cfg.t_switch       = t_switch or t_fault
    cfg.switch_state   = switch_state
    cfg.export_pfd     = 1 if export_pfd else 0
    cfg.open_digsilent = 1 if open_digsilent else 0

    def _impl():
        agent = DIgSILENTAgent(cfg)
        return agent.run_pipeline()

    return _to_json(_pf(_impl))


@mcp.tool()
def read_results_csv(csv_path: str = "", max_rows: int = 2000, as_path: bool = False, max_bytes: int = 900_000) -> str:
    """
    Read the RMS simulation results CSV and return its contents.

    If csv_path is not provided, the most recently modified *_RMS.csv file
    found anywhere inside the configured output_dir is used automatically.

    New parameters
    --------------
    as_path : bool, optional
        If True, return a small JSON object containing the absolute file
        path instead of the file contents. Use this to avoid hitting MCP
        transport size limits when passing the CSV to external LLMs.
    max_bytes : int, optional
        If > 0, the returned CSV text will be truncated to at most
        `max_bytes` bytes (UTF-8 encoded). Truncation happens at row
        boundaries when possible.

    Parameters
    ----------
    csv_path : str, optional
        Absolute path to a specific _RMS.csv file. If omitted, the latest
        file in output_dir is used.
    max_rows : int, optional
        Maximum number of data rows to return (default 2000).

    Returns
    -------
    str
        CSV text (header + up to max_rows rows) followed by metadata lines
        with file path, total rows, and truncation flag.
    """
    if csv_path:
        target = checked_path(csv_path, purpose="csv_path")
    else:
        config_path = _default_cfg_path()
        with open(config_path, "r", encoding="utf-8") as fh:
            cfg_data = json.load(fh)
        base_dir = cfg_data.get("output_dir", _HERE)
        base_dir = checked_read_tree(base_dir, purpose="results output tree")

        candidates = []
        for root, _, files in os.walk(base_dir):
            for fname in files:
                if fname.endswith("_RMS.csv"):
                    full = os.path.join(root, fname)
                    candidates.append((os.path.getmtime(full), full))

        if not candidates:
            return json.dumps({"error": f"No *_RMS.csv files found under {base_dir}"})
        candidates.sort(reverse=True)
        target = candidates[0][1]

    target = checked_path(target, purpose="results CSV path")

    if not os.path.exists(target):
        return json.dumps({"error": f"File not found: {target}"})

    if as_path:
        return json.dumps({"file_path": target})

    with open(target, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    header_idx = 0
    for i, line in enumerate(lines):
        if ";" in line or "," in line:
            header_idx = i
            break

    header_line = lines[header_idx] if lines else ""
    data_lines = lines[header_idx + 1:]
    total_rows = len(data_lines)

    # Apply max_rows pagination
    data_lines = data_lines[:max_rows]
    rows_returned = len(data_lines)
    truncated = total_rows > rows_returned

    # Build csv text while optionally enforcing max_bytes limit
    if max_bytes and max_bytes > 0:
        out_bytes = bytearray()
        # add header (may be truncated)
        hb = header_line.encode("utf-8", errors="replace")
        if len(hb) >= max_bytes:
            out_bytes.extend(hb[:max_bytes])
            csv_text = out_bytes.decode("utf-8", errors="replace")
            meta = (
                f"\n# file: {target}\n"
                f"# total_data_rows: {total_rows}\n"
                f"# rows_returned: {0}\n"
                f"# truncated_by_size: True\n"
            )
            return csv_text + meta
        out_bytes.extend(hb)

        rows_emitted = 0
        for line in data_lines:
            lb = line.encode("utf-8", errors="replace")
            if len(out_bytes) + len(lb) > max_bytes:
                break
            out_bytes.extend(lb)
            rows_emitted += 1

        csv_text = out_bytes.decode("utf-8", errors="replace")
        meta = (
            f"\n# file: {target}\n"
            f"# total_data_rows: {total_rows}\n"
            f"# rows_returned: {rows_emitted}\n"
            f"# truncated_by_size: {len(out_bytes) >= max_bytes}\n"
        )
        return csv_text + meta

    # Default (no byte-size enforcement): join header + data rows
    csv_text = header_line + "".join(data_lines)
    meta = (
        f"\n# file: {target}\n"
        f"# total_data_rows: {total_rows}\n"
        f"# rows_returned: {rows_returned}\n"
        f"# truncated: {truncated}\n"
    )
    return csv_text + meta


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]
    print(f"[MCP] Starting DIgSILENT PowerFactory server (transport={transport})", file=sys.stderr)
    mcp.run(transport=transport)
