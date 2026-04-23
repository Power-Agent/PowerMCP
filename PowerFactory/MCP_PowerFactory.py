"""
MCP Server — DIgSILENT PowerFactory Control
============================================
Exposes DIgSILENT PowerFactory simulation as FastMCP tools.

Author
------
  Andrea Pomarico

Tools
-----
  ping              Connectivity check.
  get_config        Return simulation_config.json as a JSON string.
  import_project    Import a .pfd file and activate it in PowerFactory.
  create_study_case Create/activate a study case by name (no simulation run).
  modify_parameter  Modify an object attribute by object query + variable name.
  run_loadflow      Run a load flow calculation (ComLdf) on the active study case.
  run_short_circuit Run a short-circuit calculation (ComShc) on the active study case.
  run_simulation    Run the full pipeline from simulation_config.json.
  run_custom_case   Run a one-off case with parameters supplied at call-time.
  read_results_csv  Read the latest (or a specific) RMS results CSV.

Usage
-----
  python MCP_PowerFactory.py                  # stdio transport (default)
  python MCP_PowerFactory.py --transport sse  # SSE transport on port 8000
"""


import sys
import os
import json
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

# ── FastMCP ───────────────────────────────────────────────────────────────────
from fastmcp import FastMCP

mcp = FastMCP(
    name="DIgSILENT PowerFactory Control",
    instructions=(
        "Controls DIgSILENT PowerFactory RMS transient-stability simulations. "
        "Runs simulations and saves results (CSV, grid graph PNG) to disk."
    ),
)

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CFG = os.path.join(_HERE, "simulation_config.json")
_DEFAULT_PFD = os.path.join(os.path.expanduser("~"), "Desktop", "test.pfd")

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


def _load_modules():
    """Deferred import — avoids startup crash when PowerFactory is not running."""
    from Agent_DIgSILENT import SimulationConfig, DIgSILENTAgent
    return SimulationConfig, DIgSILENTAgent


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
        return o

    return json.dumps(_clean(obj), indent=2, ensure_ascii=False)


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
    path = cfg_path or _DEFAULT_CFG
    with open(path, "r", encoding="utf-8") as fh:
        return json.dumps(json.load(fh), indent=2, ensure_ascii=False)


@mcp.tool()
def import_project(
    file_path: str = _DEFAULT_PFD,
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
        Default: ~/Desktop/test.pfd (resolved at runtime for the current user).
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    _, DIgSILENTAgent = _load_modules()
    ok, msg = _pf(DIgSILENTAgent.import_project, file_path, open_digsilent)
    return json.dumps({"success": ok, "message": msg})


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
    SimulationConfig, DIgSILENTAgent = _load_modules()
    path = cfg_path or _DEFAULT_CFG
    cfg = SimulationConfig.from_json(path)
    ok, msg = _pf(
        DIgSILENTAgent.create_study_case,
        cfg.project_path,
        case_name,
        base_study_case,
        open_digsilent,
        request_id,
    )
    return json.dumps({"success": ok, "message": msg})


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
    _, DIgSILENTAgent = _load_modules()
    ok, msg = _pf(DIgSILENTAgent.modify_parameter, object_name, variable, new_value, open_digsilent)
    return json.dumps({"success": ok, "message": msg})


@mcp.tool()
def run_loadflow(open_digsilent: bool = True) -> str:
    """
    Run a load flow calculation (ComLdf) on the currently active study case.

    Parameters
    ----------
    open_digsilent : bool
        If True (default), requests the PowerFactory GUI window via app.Show().

    Returns
    -------
    str
        JSON string with success flag and message.
    """
    _, DIgSILENTAgent = _load_modules()
    ok, msg = _pf(DIgSILENTAgent.load_flow, open_digsilent)
    return json.dumps({"success": ok, "message": msg})


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
    _, DIgSILENTAgent = _load_modules()
    ok, msg = _pf(DIgSILENTAgent.short_circuit, open_digsilent)
    return json.dumps({"success": ok, "message": msg})


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
    path = cfg_path or _DEFAULT_CFG
    cfg = SimulationConfig.from_json(path)
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
    path = cfg_path or _DEFAULT_CFG
    cfg = SimulationConfig.from_json(path)
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
def read_results_csv(csv_path: str = "", max_rows: int = 2000) -> str:
    """
    Read the RMS simulation results CSV and return its contents.

    If csv_path is not provided, the most recently modified *_RMS.csv file
    found anywhere inside the configured output_dir is used automatically.

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
        target = csv_path
    else:
        with open(_DEFAULT_CFG, "r", encoding="utf-8") as fh:
            cfg_data = json.load(fh)
        base_dir = cfg_data.get("output_dir", _HERE)

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

    if not os.path.exists(target):
        return json.dumps({"error": f"File not found: {target}"})

    with open(target, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    header_idx = 0
    for i, line in enumerate(lines):
        if ";" in line or "," in line:
            header_idx = i
            break

    header_line = lines[header_idx] if lines else ""
    data_lines  = lines[header_idx + 1:]
    total_rows  = len(data_lines)
    truncated   = total_rows > max_rows
    data_lines  = data_lines[:max_rows]

    csv_text = header_line + "".join(data_lines)
    meta = (
        f"\n# file: {target}\n"
        f"# total_data_rows: {total_rows}\n"
        f"# rows_returned: {min(total_rows, max_rows)}\n"
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
