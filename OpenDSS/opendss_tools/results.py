"""Results-domain MCP tools."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from utils.responses import _err, _ok, _require_solution


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


def register_results_tools(mcp: FastMCP) -> None:
    mcp.tool()(get_results_summary_records)
    mcp.tool()(get_voltage_mag_ln_nodes_records)
    mcp.tool()(get_powers_p_records)
