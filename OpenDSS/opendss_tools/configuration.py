"""Configuration-domain MCP tools (compile, clear)."""

from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from core.engine import dss
from utils.responses import _err, _ok


def compile_opendss_file(dss_file: str, force_recompile: bool = False) -> Dict[str, Any]:
    """Compile a master DSS file (ClearAll + Compile).

    If the same resolved path is already loaded, skips compile unless ``force_recompile`` is True
    (e.g. user wants to recompile the model to clean changes). A different ``dss_file`` loads a new model and always compiles.
    After ``clear_all_opendss_memory``, the next call compiles as usual.

    Returns dss_file, circuit_readiness, circuit_loaded, and whether the compile was skipped.
    """
    resolved = str(Path(dss_file).resolve())
    if (
        state.circuit_loaded
        and state.last_compiled_dss_file is not None
        and resolved == state.last_compiled_dss_file
        and not force_recompile
    ):
        readiness = dss_tools.configuration.circuit_readiness()
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": True,
                "already_compiled": True,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": state.solution_available,
            }
        )
    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness = dss_tools.configuration.circuit_readiness()
        state.circuit_loaded = True
        state.solution_available = False
        state.last_compiled_dss_file = resolved
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": False,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as e:
        state.circuit_loaded = False
        state.solution_available = False
        state.last_compiled_dss_file = None
        return _err(str(e))


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll); resets circuit_loaded, solution_available, and last compiled path."""
    try:
        dss.text("ClearAll")
        state.circuit_loaded = False
        state.solution_available = False
        state.last_compiled_dss_file = None
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as e:
        return _err(str(e))


def register_configuration_tools(mcp: FastMCP) -> None:
    mcp.tool()(compile_opendss_file)
    mcp.tool()(clear_all_opendss_memory)
