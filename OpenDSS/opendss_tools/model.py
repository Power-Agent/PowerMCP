"""Model-domain MCP tools."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from utils.responses import _err, _ok, _require_circuit_loaded


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


def add_line_in_vsource(
    add_meter: bool = True,
    add_monitors: bool = False,
) -> Dict[str, Any]:
    """Insert feeder-head line at Vsource; optional energymeter and monitors (py-dss-toolkit model.add_line_in_vsource)."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.add_line_in_vsource(add_meter=add_meter, add_monitors=add_monitors)
        state.solution_available = False
        return _ok(
            {
                "added": True,
                "add_meter": add_meter,
                "add_monitors": add_monitors,
            }
        )
    except Exception as e:
        return _err(str(e))


def register_model_tools(mcp: FastMCP) -> None:
    mcp.tool()(get_model_summary_records)
    mcp.tool()(get_buses_records)
    mcp.tool()(get_lines_records)
    mcp.tool()(add_line_in_vsource)
