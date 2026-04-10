"""Simulation-domain MCP tools."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from utils.responses import _err, _ok, _require_circuit_loaded


def solve_snapshot(
    control_mode: str = "Static",
    max_iterations: int = 15,
    max_control_iter: int = 10,
) -> Dict[str, Any]:
    """Run a snapshot power-flow solve; payload includes snapshot_solve_status and solution_available."""
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
        state.solution_available = True
        return _ok({**status, "solution_available": True})
    except Exception as e:
        state.solution_available = False
        return _err(str(e))


def register_simulation_tools(mcp: FastMCP) -> None:
    mcp.tool()(solve_snapshot)
