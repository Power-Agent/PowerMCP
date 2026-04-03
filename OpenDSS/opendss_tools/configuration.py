"""Configuration-domain MCP tools (compile, clear)."""

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from core.engine import dss
from utils.responses import _err, _ok


def compile_opendss_file(dss_file: str) -> Dict[str, Any]:
    """Compile a master DSS file (ClearAll + Compile).

    Returns dss_file, circuit_readiness, and circuit_loaded (MCP session flag).
    """
    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness = dss_tools.configuration.circuit_readiness()
        state.circuit_loaded = True
        state.solution_available = False
        return _ok(
            {
                "dss_file": dss_file,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as e:
        state.circuit_loaded = False
        state.solution_available = False
        return _err(str(e))


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll) and sets circuit_loaded to false."""
    try:
        dss.text("ClearAll")
        state.circuit_loaded = False
        state.solution_available = False
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as e:
        return _err(str(e))


def register_configuration_tools(mcp: FastMCP) -> None:
    mcp.tool()(compile_opendss_file)
    mcp.tool()(clear_all_opendss_memory)
