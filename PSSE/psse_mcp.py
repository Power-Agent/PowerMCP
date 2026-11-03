import sys
import os
import re
import json
import io
import importlib
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Optional, Any, Tuple

# Initialize MCP server
mcp = FastMCP("PSSE 35+ Positive Sequence Load Flow Program")


def _version_key(version_str: str) -> Tuple[int, ...]:
    """Turn a version string like '36.4.0' or '35.4' into a sortable tuple of ints."""
    parts = re.findall(r"\d+", version_str or "")
    return tuple(int(p) for p in parts) if parts else (0,)


def _is_valid_psspy_dir(psspy_path: str, exe_path: str) -> bool:
    """
    Confirm a candidate psspy directory actually contains the psspy module
    (as "psspy.pyc" or "psspy.py") rather than being an empty/incomplete
    install folder left behind by a partial installation.
    """
    if not (psspy_path and exe_path and os.path.isdir(psspy_path) and os.path.isdir(exe_path)):
        return False
    return any(
        os.path.isfile(os.path.join(psspy_path, f"psspy{ext}"))
        for ext in (".pyc", ".py", ".pyd")
    )


def _psse_candidates_from_registry(allowed_majors, pyver: str):
    """
    Enumerate PSSE installations from the Windows registry.

    PSSE's installer writes entries under HKLM\\SOFTWARE\\PTI\\PSSE <major>\\<build>\\Product Paths
    with values such as PsseInstallPath, PsseExePath (PSSBIN) and one
    PsseLocalPsspy<pyver>Path value per supported Python version (casing varies,
    e.g. "Psselocalpsspy313Path" vs "PsseLocalPsspy314Path"), so lookups are
    done case-insensitively.
    """
    candidates = []
    try:
        import winreg
    except ImportError:
        return candidates  # not running on Windows

    psspy_value_name = f"psselocalpsspy{pyver}path"

    for major in allowed_majors:
        root_key = rf"SOFTWARE\PTI\PSSE {major}"
        try:
            pkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root_key)
        except OSError:
            continue

        with pkey:
            i = 0
            while True:
                try:
                    build_name = winreg.EnumKey(pkey, i)
                except OSError:
                    break
                i += 1

                try:
                    bkey = winreg.OpenKey(pkey, rf"{build_name}\Product Paths")
                except OSError:
                    continue

                with bkey:
                    values = {}
                    j = 0
                    while True:
                        try:
                            name, data, _ = winreg.EnumValue(bkey, j)
                        except OSError:
                            break
                        values[name.lower()] = data
                        j += 1

                psspy_path = values.get(psspy_value_name)
                exe_path = values.get("psseexepath")
                version_str = values.get("version") or f"{major}.{build_name}"
                if _is_valid_psspy_dir(psspy_path, exe_path):
                    candidates.append((_version_key(version_str), major, version_str, psspy_path, exe_path))

    return candidates


def _psse_candidates_from_filesystem(allowed_majors, pyver: str):
    """Fallback discovery by scanning default PTI install directories."""
    candidates = []
    for major in allowed_majors:
        for root in (r"C:\Program Files\PTI", r"C:\Program Files (x86)\PTI"):
            psse_dir = os.path.join(root, f"PSSE{major}")
            if not os.path.isdir(psse_dir):
                continue
            for entry in os.listdir(psse_dir):
                version_dir = os.path.join(psse_dir, entry)
                if not os.path.isdir(version_dir):
                    continue
                psspy_path = os.path.join(version_dir, f"PSSPY{pyver}")
                exe_path = os.path.join(version_dir, "PSSBIN")
                if _is_valid_psspy_dir(psspy_path, exe_path):
                    candidates.append((_version_key(entry), major, entry, psspy_path, exe_path))
    return candidates


def _discover_psse_paths() -> Tuple[int, str, str, str]:
    """
    Locate an installed PSSE version (35 or 36) whose bundled psspy module
    matches the Python interpreter currently running this MCP server.

    Resolution order:
      1. Manual override via PSSE_PSSPY_PATH / PSSE_EXE_PATH env vars (with
         optional PSSE_VERSION to pick which "psseXX" module to import).
      2. Windows registry (HKLM\\SOFTWARE\\PTI\\PSSE 35|36), populated by the
         PSSE installer with exact paths per supported Python version.
      3. Filesystem scan of the default "C:\\Program Files\\PTI\\PSSE35|36"
         install locations, merged in to cover installs the registry doesn't
         (yet) know about.

    Among all matches, the highest PSSE version is selected. Set PSSE_VERSION
    to "35" or "36" to restrict discovery to a single major version.

    Returns (major_version, version_str, psspy_path, exe_path).
    """
    pyver = f"{sys.version_info.major}{sys.version_info.minor}"  # e.g. "311"

    forced_major = os.environ.get("PSSE_VERSION")
    allowed_majors = [int(forced_major)] if forced_major else [36, 35]

    # 1. Manual override -----------------------------------------------------
    override_psspy = os.environ.get("PSSE_PSSPY_PATH")
    override_exe = os.environ.get("PSSE_EXE_PATH")
    if override_psspy and override_exe:
        major = int(forced_major) if forced_major else 36
        return major, "manual-override", override_psspy, override_exe

    # 2. Windows registry, merged with 3. filesystem scan ---------------------
    # The registry is queried first since it's authoritative and fast, but it
    # can be stale/incomplete (e.g. missing an entry for a version that was
    # installed without updating that key), so filesystem results are merged
    # in rather than used only as an all-or-nothing fallback. Candidates are
    # de-duplicated by psspy path, keeping the version with the most info.
    candidates_by_path = {}
    for candidate in _psse_candidates_from_registry(allowed_majors, pyver):
        candidates_by_path[os.path.normcase(candidate[3])] = candidate
    for candidate in _psse_candidates_from_filesystem(allowed_majors, pyver):
        candidates_by_path.setdefault(os.path.normcase(candidate[3]), candidate)
    candidates = list(candidates_by_path.values())

    if not candidates:
        raise RuntimeError(
            f"Could not find a PSSE 35/36 installation with Python {pyver} support "
            f"(interpreter: {sys.executable}). Checked the Windows registry "
            r"(HKLM\SOFTWARE\PTI\PSSE 35|36) and default install directories "
            r"(C:\Program Files\PTI\PSSE35|36). If PSSE is installed elsewhere, "
            "set the PSSE_PSSPY_PATH and PSSE_EXE_PATH environment variables "
            "to the PSSPY<pyver> and PSSBIN directories respectively."
        )

    candidates.sort(key=lambda c: c[0], reverse=True)
    _, major, version_str, psspy_path, exe_path = candidates[0]
    return major, version_str, psspy_path, exe_path


# Import and initialize PSSE Python library
# Path is auto-discovered (registry, then filesystem scan) to find the highest
# installed PSSE version whose psspy module matches this Python interpreter's
# version. See _discover_psse_paths() for details and override env vars.
_psse_major, _psse_version_str, _psse_psspy_path, _psse_exe_path = _discover_psse_paths()

sys.path.append(_psse_psspy_path)
sys.path.append(_psse_exe_path)
os.environ['PATH'] = _psse_psspy_path + os.pathsep + os.environ['PATH']
os.environ['PATH'] = _psse_exe_path + os.pathsep + os.environ['PATH']

importlib.import_module(f"psse{_psse_major}")

import psspy
psspy.psseinit(50)

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
# Native stdout protection
# ---------------------------------------------------------------------------
#
# Many psspy calls (fdns, nsol, gendsp_2, etc.) write solution/progress text
# to PSSE's "standard destination" (islct=1) as a side effect, which in this
# headless context lands on the process's real stdout -- the same stream
# FastMCP's stdio transport uses for JSON-RPC framing. If that text is not
# intercepted, it corrupts the protocol stream mid-message and permanently
# wedges the server (every subsequent request times out, even ones that
# never touch psspy, since the transport itself is desynced) until it is
# restarted. Wrap every psspy call site in a throwaway stdout capture so
# native output can never reach the real stream. Handlers that intentionally
# want the captured text (_handle_error_only_report/_listing) perform their
# own inner redirect-and-capture, which nests safely inside this one.
import contextlib


@contextlib.contextmanager
def _suppress_native_stdout():
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout


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
        with _suppress_native_stdout():
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
        with _suppress_native_stdout():
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
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            result = handler(spec, arguments)
        finally:
            sys.stdout = old_stdout
        # Some psspy functions (e.g. diff, accc_with_trip_2) print their real
        # output as a console side effect rather than returning it as a value.
        # Surface anything captured that the handler itself didn't already
        # return (handlers with return_type error_only_report/_listing put
        # it under "report" themselves), so nothing is silently lost -- while
        # still keeping it off the real stdout/JSON-RPC stream.
        captured = buf.getvalue()
        if captured and "report" not in result:
            result["_console_output"] = captured
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
