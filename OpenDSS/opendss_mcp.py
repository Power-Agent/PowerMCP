"""OpenDSS MCP server powered by py-dss-toolkit."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from py_dss_interface import DSS
from py_dss_toolkit import dss_tools

# --- engine + toolkit facade (single session) ---
_dss = DSS()
dss_tools.update_dss(_dss)

# True after a successful compile_opendss_file; False after clear_all_opendss_memory (or failed compile).
_circuit_loaded: bool = False

# True after a successful solve_opendss_snapshot; False after compile (new case) or clear_all.
_solution_available: bool = False


def _ok(payload: Any = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    if payload is not None:
        out["payload"] = payload
    return out


def _err(msg: str) -> Dict[str, Any]:
    return {"success": False, "error": msg}


def _require_circuit_loaded() -> Optional[Dict[str, Any]]:
    """Return an error response if no case has been compiled in this MCP session."""
    if not _circuit_loaded:
        return _err("No circuit loaded; call compile_opendss_file first.")
    return None


def _require_solution() -> Optional[Dict[str, Any]]:
    """Return an error response if no snapshot solve has completed since compile/clear."""
    if not _solution_available:
        return _err("No snapshot solution; call solve_opendss_snapshot first.")
    return None


mcp = FastMCP("PyDSS-MCP")


@mcp.tool()
def compile_opendss_file(dss_file: str) -> Dict[str, Any]:
    """Compile a master DSS file (ClearAll + Compile).

    Returns dss_file, circuit_readiness, and circuit_loaded (MCP session flag).
    """
    global _circuit_loaded, _solution_available
    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness = dss_tools.configuration.circuit_readiness()
        _circuit_loaded = True
        _solution_available = False
        return _ok(
            {
                "dss_file": dss_file,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as e:
        _circuit_loaded = False
        _solution_available = False
        return _err(str(e))


@mcp.tool()
def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll) and sets circuit_loaded to false."""
    global _circuit_loaded, _solution_available
    try:
        _dss.text("ClearAll")
        _circuit_loaded = False
        _solution_available = False
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_model_summary_records() -> Dict[str, Any]:
    """Model summary counts and stats (model._summary_model_records). Requires a compiled circuit."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.model._summary_model_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_buses_records() -> Dict[str, Any]:
    """Bus-level records for every bus (model._buses_records). Requires a compiled circuit."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.model._buses_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_lines_records() -> Dict[str, Any]:
    """Line element records (model._lines_records). Payload is null if there are no lines. Requires a compiled circuit."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.model._lines_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def add_line_in_vsource(
    add_meter: bool = True,
    add_monitors: bool = False,
) -> Dict[str, Any]:
    """Insert feeder-head line at Vsource; optional energymeter and monitors (py-dss-toolkit model.add_line_in_vsource)."""
    global _solution_available
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.add_line_in_vsource(add_meter=add_meter, add_monitors=add_monitors)
        _solution_available = False
        return _ok(
            {
                "added": True,
                "add_meter": add_meter,
                "add_monitors": add_monitors,
            }
        )
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def solve_opendss_snapshot(
    control_mode: str = "Static",
    max_iterations: int = 15,
    max_control_iter: int = 10,
) -> Dict[str, Any]:
    """Run a snapshot power-flow solve; payload includes snapshot_solve_status and solution_available."""
    global _solution_available
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.simulation.solve_snapshot(
            control_mode=control_mode,
            max_iterations=max_iterations,
            max_control_iter=max_control_iter,
        )
        status = dss_tools.simulation.snapshot_solve_status()
        _solution_available = True
        return _ok({**status, "solution_available": True})
    except Exception as e:
        _solution_available = False
        return _err(str(e))


@mcp.tool()
def get_results_summary_records() -> Dict[str, Any]:
    """Feeder summary after solve (results._summary_records). Requires a snapshot solution."""
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.results._summary_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_voltage_mag_ln_nodes_records() -> Dict[str, Any]:
    """Line-to-neutral nodal voltage magnitudes (results._voltage_mag_ln_nodes_records). Requires a snapshot solution."""
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.results._voltage_mag_ln_nodes_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_powers_p_records() -> Dict[str, Any]:
    """Real power P by PD element (results._powers_p_records). Requires a snapshot solution."""
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.results._powers_p_records
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_voltage_profile_plotly_figure(
    voltage_type: str = "ln",
    title: Optional[str] = "Voltage Profile",
) -> Dict[str, Any]:
    """Use this MCP tool when the user asks for voltage profile (voltage
    versus distance along the feeder from the feeder head), as Plotly figure
    JSON from py-dss-toolkit (``interactive_view.voltage_profile``).

    Do not recreate this plot from nodal voltage tables alone unless the user explicitly
    asks for a custom visualization.

    Requires ``solve_opendss_snapshot`` first. The toolkit typically needs an energymeter;
    use ``add_line_in_vsource(add_meter=True)`` if the case has none, then call
    ``solve_opendss_snapshot`` again.

    Returns ``payload.plotly_json`` (Plotly figure as a JSON-serializable dict).
    """
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    try:
        fig = dss_tools.interactive_view.voltage_profile(
            voltage_type=voltage_type,  # type: ignore[arg-type]
            title=title,
            show=False,
        )
        if fig is None:
            return _err("Voltage profile returned no figure.")
        return _ok({"plotly_json": json.loads(fig.to_json())})
    except Exception as e:
        return _err(str(e))


@mcp.tool()
def get_opendss_circuit_map_plotly_figure(
    parameter: str = "active power",
    title: Optional[str] = "Circuit Plot",
    warn_zero_coord_buses: bool = False,
) -> Dict[str, Any]:
    """Use this MCP tool when the user wants a circuit map (one-line style Plotly diagram) of the
    solved feeder using bus X/Y coordinates, colored by a chosen quantity.

    Calls ``interactive_view.circuit_plot`` (see py-dss-toolkit
    ``examples/dss_tools/circuit_interactive_view.py``). Common ``parameter`` values include
    ``active power``, ``reactive power``, ``voltage``, ``phases``, ``voltage violations``,
    ``thermal violations``, ``distance``, and ``user numerical defined`` / ``user categorical defined``
    (user-defined modes may require setting toolkit view settings first).

    Do not recreate this map from bus/line tables alone unless the user explicitly asks for a custom diagram.

    Requires ``solve_opendss_snapshot`` first. Bus coordinates must be present (e.g. ``BusCoords`` in DSS);
    set ``warn_zero_coord_buses`` to surface buses at (0, 0).

    Returns ``payload.plotly_json`` (Plotly figure as a JSON-serializable dict).
    """
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    try:
        fig = dss_tools.interactive_view.circuit_plot(
            parameter=parameter,  # type: ignore[arg-type]
            title=title,
            show=False,
            warn_zero_coord_buses=warn_zero_coord_buses,
        )
        return _ok({"plotly_json": json.loads(fig.to_json())})
    except Exception as e:
        return _err(str(e))


if __name__ == "__main__":
    mcp.run(transport="stdio")
