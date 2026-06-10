import sys
import os
import json
import io
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional, Any

# Initialize MCP server
mcp = FastMCP("PSSE 35+ Positive Sequence Load Flow Program")

# ---------------------------------------------------------------------------
# Lazy, memoized PSS/E engine initialization.
#
# psspy lives in a local PSS/E install dir and psseinit() starts the engine.
# Both used to run at import time, which crashed this module on any machine
# without PSS/E and blocked packaging/discovery. They now run once, on the first
# tool call. The PSSPYxxx / PSSBIN dirs come from ~/.powermcp/config.toml (keys
# psse.python_lib, psse.bin) when powermcp is installed, else fall back to the
# historical hardcoded paths so a raw checkout keeps working.
# ---------------------------------------------------------------------------
_PSSE_LEGACY = {
    "python_lib": r"C:\Program Files\PTI\PSSE36\36.2\PSSPY311",
    "bin": r"C:\Program Files\PTI\PSSE36\36.2\PSSBIN",
}

psspy = None  # imported lazily by _ensure_psse()
_psse_ready = False


def _resolve_psse_paths():
    """Return (python_lib, bin): config when available, else legacy defaults."""
    try:
        from powermcp.config import get_path
        return (get_path("psse", "python_lib", must_exist=False),
                get_path("psse", "bin", must_exist=False))
    except Exception:
        return _PSSE_LEGACY["python_lib"], _PSSE_LEGACY["bin"]


def _ensure_psse():
    """Inject PSS/E paths, import psspy, and call psseinit(50) exactly once."""
    global psspy, _psse_ready
    if _psse_ready:
        return psspy
    python_lib, bin_dir = _resolve_psse_paths()
    for p in (python_lib, bin_dir):
        if not p:
            continue
        if p not in sys.path:
            sys.path.insert(0, p)
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
    try:
        import psse36  # noqa: F401  (vendor shim that sets up further paths)
        import psspy as _psspy
    except Exception as e:
        raise RuntimeError(
            "Could not import PSS/E (psspy). Ensure PSS/E is installed and its paths "
            "are configured: `powermcp config set psse.python_lib <PSSPYxxx dir>` and "
            "`powermcp config set psse.bin <PSSBIN dir>`. Original error: " + repr(e)
        )
    _psspy.psseinit(50)  # 50 = PSS/E 35+ bus mode; do NOT change
    psspy = _psspy
    _psse_ready = True
    return psspy

# Path to JSON command reference files
JSON_DIR = Path(__file__).parent / "psspy_command_json"


def _lookup_error(ierr, error_codes):
    """Look up an error code in the error_codes list from the JSON spec."""
    if not error_codes:
        return f"error code {ierr}"
    for entry in error_codes:
        val = entry.get("value", "").strip()
        # Match "= 0", "= 1", etc.
        if val.lstrip("= ") == str(ierr):
            return entry.get("description", f"error code {ierr}")
    return f"error code {ierr} (undocumented)"


def _coerce_arg(value, name, spec_params):
    """Attempt to keep argument as-is; callers are responsible for types."""
    return value


def _get_psspy_func(func_name):
    """Get a psspy function by name."""
    func = getattr(psspy, func_name, None)
    if func is None:
        raise ValueError(f"psspy.{func_name} does not exist")
    return func


def _build_kwargs(spec, provided_args):
    """Build kwargs dict from spec parameters and provided arguments."""
    kwargs = {}
    for param in spec.get("parameters", []):
        name = param["name"]
        if name in provided_args:
            kwargs[name] = provided_args[name]
    return kwargs


# ---------------------------------------------------------------------------
# One handler per return_type
# ---------------------------------------------------------------------------

def _handle_error_only(spec, args):
    """ierr = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    ierr = func(**kwargs)
    error_codes = spec.get("error_codes", [])
    if ierr == 0:
        return {"status": "success", "ierr": 0}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_only_report(spec, args):
    """ierr = func(...) — function prints report text as side effect.
    Captures PSSE output buffer and returns it."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)

    # Redirect PSSE output to a string buffer
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        ierr = func(**kwargs)
    finally:
        sys.stdout = old_stdout

    report_text = buf.getvalue()
    error_codes = spec.get("error_codes", [])

    result = {"ierr": ierr, "report": report_text}
    if ierr == 0:
        result["status"] = "success"
    else:
        result["status"] = "error"
        result["message"] = _lookup_error(ierr, error_codes)
    return result


def _handle_error_only_listing(spec, args):
    """ierr = func(...) — function lists models/data as side effect."""
    # Same capture strategy as report
    return _handle_error_only_report(spec, args)


def _handle_error_only_output_channel(spec, args):
    """ierr = func(...) — adds a simulation output channel."""
    # Same as error_only; the side effect is channel registration, not text
    return _handle_error_only(spec, args)


def _handle_error_only_write_file(spec, args):
    """ierr = func(...) — writes output to a file."""
    return _handle_error_only(spec, args)


def _handle_error_and_scalar(spec, args):
    """ierr, val = func(...)  where val is rval/ival/cval/lval/cmpval."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    value = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "value"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: value}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_array(spec, args):
    """ierr, array = func(...)  where array is rarray/iarray/carray/xarray."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    array = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "array"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: array}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_count(spec, args):
    """ierr, count = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    count = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "count"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: count}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_string(spec, args):
    """ierr, string = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    string_val = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "string"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: string_val}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_types(spec, args):
    """ierr, types = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    types_val = result[1]
    error_codes = spec.get("error_codes", [])

    if ierr == 0:
        return {"status": "success", "ierr": 0, "types": types_val}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_model(spec, args):
    """ierr, model = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    model = result[1]
    error_codes = spec.get("error_codes", [])

    if ierr == 0:
        return {"status": "success", "ierr": 0, "model": model}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_record(spec, args):
    """ierr, realaro/intgaro = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    record = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "record"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: record}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_value(spec, args):
    """ierr, <named_value> = func(...) — catch-all for single named returns."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    value = result[1]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]
    val_name = ret_names[1] if len(ret_names) > 1 else "value"

    if ierr == 0:
        return {"status": "success", "ierr": 0, val_name: value}
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_multi_value(spec, args):
    """ierr, val1, val2, ... = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]

    if ierr == 0:
        output = {"status": "success", "ierr": 0}
        for i, val in enumerate(result[1:], start=1):
            name = ret_names[i] if i < len(ret_names) else f"value_{i}"
            output[name] = val
        return output
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_error_and_array_plus(spec, args):
    """ierr, array, extra... = func(...)"""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ierr = result[0]
    error_codes = spec.get("error_codes", [])
    ret_names = [r["name"] for r in spec.get("return_values", [])]

    if ierr == 0:
        output = {"status": "success", "ierr": 0}
        for i, val in enumerate(result[1:], start=1):
            name = ret_names[i] if i < len(ret_names) else f"value_{i}"
            output[name] = val
        return output
    return {"status": "error", "ierr": ierr, "message": _lookup_error(ierr, error_codes)}


def _handle_value_only(spec, args):
    """val = func(...) — no ierr in return."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ret_names = [r["name"] for r in spec.get("return_values", [])]

    if isinstance(result, tuple):
        output = {"status": "success"}
        for i, val in enumerate(result):
            name = ret_names[i] if i < len(ret_names) else f"value_{i}"
            output[name] = val
        return output

    val_name = ret_names[0] if ret_names else "value"
    return {"status": "success", val_name: result}


def _handle_multi_value(spec, args):
    """val1, val2 = func(...) — multiple returns, no ierr."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    result = func(**kwargs)
    ret_names = [r["name"] for r in spec.get("return_values", [])]

    output = {"status": "success"}
    if isinstance(result, tuple):
        for i, val in enumerate(result):
            name = ret_names[i] if i < len(ret_names) else f"value_{i}"
            output[name] = val
    else:
        val_name = ret_names[0] if ret_names else "value"
        output[val_name] = result
    return output


def _handle_void(spec, args):
    """func(...) — no return value."""
    func = _get_psspy_func(spec["function_name"])
    kwargs = _build_kwargs(spec, args)
    func(**kwargs)
    return {"status": "success"}


# ---------------------------------------------------------------------------
# Dispatch table mapping return_type -> handler
# ---------------------------------------------------------------------------

_HANDLERS = {
    "error_only":               _handle_error_only,
    "error_only_report":        _handle_error_only_report,
    "error_only_listing":       _handle_error_only_listing,
    "error_only_output_channel": _handle_error_only_output_channel,
    "error_only_write_file":    _handle_error_only_write_file,
    "error_and_scalar":         _handle_error_and_scalar,
    "error_and_array":          _handle_error_and_array,
    "error_and_count":          _handle_error_and_count,
    "error_and_string":         _handle_error_and_string,
    "error_and_types":          _handle_error_and_types,
    "error_and_model":          _handle_error_and_model,
    "error_and_record":         _handle_error_and_record,
    "error_and_value":          _handle_error_and_value,
    "error_and_multi_value":    _handle_error_and_multi_value,
    "error_and_array_plus":     _handle_error_and_array_plus,
    "value_only":               _handle_value_only,
    "multi_value":              _handle_multi_value,
    "void":                     _handle_void,
}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def open_case(case: str) -> Dict[str, Any]:
    """
    Open a PSSE case file.

    Args:
        case: Filename with .sav extension.

    Returns:
        Dict with status and case information
    """
    try:
        _ensure_psse()
        ierr = psspy.case(case)
        err, bus_data = psspy.abuscount(flag=2)
        err, branch_data = psspy.abrncount(flag=4)
        err, gen_data = psspy.amachcount(flag=4)

        if err == 0:
            return {
                'status': 'success',
                'case_info': {
                    'path': os.path.abspath(case),
                    'num_buses': bus_data or 0,
                    'num_branches': branch_data or 0,
                    'num_generators': gen_data or 0
                }
            }
        return {'status': 'error', 'ierr': err}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def solve_case() -> Dict[str, Any]:
    """
    Solves a powerflow case using PSSE Newton-Raphson method.

    Returns:
        Dict with status and result code
    """
    try:
        _ensure_psse()
        ierr = psspy.nsol()
        if ierr == 0:
            return {'status': 'success', 'ierr': 0}
        # Load nsol error codes from JSON if available
        spec_path = JSON_DIR / "nsol.json"
        error_codes = []
        if spec_path.exists():
            with open(spec_path, encoding="utf-8") as f:
                spec = json.load(f)
            error_codes = spec.get("error_codes", [])
        return {'status': 'error', 'ierr': ierr, 'message': _lookup_error(ierr, error_codes)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def run_psspy_command(function_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute any psspy API command by name, using its JSON reference spec.

    Loads the command definition from the JSON reference, determines the
    return type, calls the appropriate handler, and returns structured output.

    Args:
        function_name: Name of the psspy function (e.g. "abusreal", "pout", "brndat").
        arguments: Dict of argument names to values. Use Python syntax param names
                   (lowercase). Omit to use defaults.

    Returns:
        Dict with status, return values, and error info if applicable.
        The keys in the response match the return value names from the Python syntax.
    """
    if arguments is None:
        arguments = {}

    # Load the JSON spec for this function
    spec_path = JSON_DIR / f"{function_name}.json"
    if not spec_path.exists():
        return {"status": "error", "message": f"No JSON spec found for '{function_name}'. Check _index.json for available functions."}

    try:
        with open(spec_path, encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as e:
        return {"status": "error", "message": f"Failed to load spec for '{function_name}': {e}"}

    return_type = spec.get("return_type", "void")
    handler = _HANDLERS.get(return_type)
    if handler is None:
        return {"status": "error", "message": f"Unknown return_type '{return_type}' for '{function_name}'"}

    try:
        _ensure_psse()
        result = handler(spec, arguments)
        # Attach function metadata for AI context
        result["_function"] = function_name
        result["_return_type"] = return_type
        return result
    except Exception as e:
        return {"status": "error", "message": f"psspy.{function_name} raised: {e}"}


@mcp.tool()
def lookup_psspy_command(function_name: str) -> Dict[str, Any]:
    """
    Look up the API reference for a psspy function without executing it.

    Returns the full JSON spec including description, parameters, return values,
    allowed values, and error codes.

    Args:
        function_name: Name of the psspy function (e.g. "abusreal", "pout").

    Returns:
        The full API reference dict from the parsed documentation.
    """
    spec_path = JSON_DIR / f"{function_name}.json"
    if not spec_path.exists():
        return {"status": "error", "message": f"No spec found for '{function_name}'."}

    with open(spec_path, encoding="utf-8") as f:
        return json.load(f)


@mcp.tool()
def search_psspy_commands(query: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Search the psspy API index for functions matching a query.

    Searches function names and descriptions. Optionally filter by category.

    Args:
        query: Search term (matched against function name and description).
        category: Optional category filter (e.g. "Power Flow Operation", "Bus Data").

    Returns:
        Dict with matching functions (name, category, syntax, description snippet).
    """
    index_path = JSON_DIR / "_index.json"
    if not index_path.exists():
        return {"status": "error", "message": "Index file not found. Run sphinx2json.py first."}

    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    query_lower = query.lower()
    matches = []
    for entry in index:
        if category and entry.get("category", "").lower() != category.lower():
            continue
        name = entry.get("function_name", "").lower()
        desc = entry.get("description", "").lower()
        if query_lower in name or query_lower in desc:
            matches.append(entry)

    return {"status": "success", "count": len(matches), "results": matches[:50]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
