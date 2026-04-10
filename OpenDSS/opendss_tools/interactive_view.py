"""Interactive Plotly figure MCP tools."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from utils.responses import _err, _ok, _require_solution


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


def register_interactive_view_tools(mcp: FastMCP) -> None:
    mcp.tool()(get_voltage_profile_plotly_figure)
    mcp.tool()(get_opendss_circuit_map_plotly_figure)
