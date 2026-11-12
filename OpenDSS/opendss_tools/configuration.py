"""Configuration-domain MCP tools (compile, clear)."""

from pathlib import Path
from typing import Any, Dict

from mcp.server.mcpserver import MCPServer as FastMCP
from py_dss_toolkit import dss_tools

from core import state
import core.engine as engine
from powermcp.sandbox import (
    PathNotAllowed,
    allowed_roots,
    checked_path,
    checked_read_tree,
)
from utils.responses import _err, _ok


def _compiled_circuit_details() -> Dict[str, Any]:
    """Return engine-level counts and reject empty/partially compiled circuits."""
    dss = engine.ensure_engine()
    circuit = dss.circuit
    num_buses = int(circuit.num_buses)
    num_elements = int(circuit.num_ckt_elements)
    readiness = dss_tools.configuration.circuit_readiness()

    if num_buses <= 0 or num_elements <= 0 or readiness.get("ready") is False:
        raise RuntimeError(
            "OpenDSS did not produce a usable circuit after compilation "
            f"(buses={num_buses}, elements={num_elements}, "
            f"readiness={readiness.get('code', 'unknown')}: "
            f"{readiness.get('message', '')}). Check Redirect/Compile paths "
            "and OpenDSS error output; the model was not accepted."
        )
    return {
        "circuit_readiness": readiness,
        "num_buses": num_buses,
        "num_elements": num_elements,
    }


def _reset_failed_compile() -> None:
    """Discard a partial DSS model so it cannot be mistaken for a loaded case."""
    state.circuit_loaded = False
    state.solution_available = False
    state.last_compiled_dss_file = None
    try:
        engine.ensure_engine().text("ClearAll")
    except Exception:
        # Preserve the original compile/validation failure for the caller.
        pass


def compile_opendss_file(dss_file: str, force_recompile: bool = False) -> Dict[str, Any]:
    """Compile and verify a master DSS file (ClearAll + Compile).

    A successful Compile command is not sufficient: OpenDSS can report a missing
    Redirect file while leaving a partial circuit. The tool verifies that the
    resulting circuit has buses and circuit elements before marking it loaded.
    """
    try:
        dss_file = checked_path(dss_file, purpose="dss_file")
        # A DSS model may Redirect/Compile sibling files. Preflight the whole
        # project tree when containment is enabled; preserve the historical
        # single-file behavior when the operator has not configured roots.
        if allowed_roots():
            checked_read_tree(str(Path(dss_file).parent), purpose="DSS input tree")
    except PathNotAllowed as exc:
        return _err(str(exc))

    resolved = str(Path(dss_file).resolve())
    if (
        state.circuit_loaded
        and state.last_compiled_dss_file is not None
        and resolved == state.last_compiled_dss_file
        and not force_recompile
    ):
        try:
            details = _compiled_circuit_details()
        except Exception as exc:
            _reset_failed_compile()
            return _err(str(exc))
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": True,
                "already_compiled": True,
                **details,
                "circuit_loaded": True,
                "solution_available": state.solution_available,
            }
        )

    try:
        dss_tools.configuration.compile_dss(dss_file)
        details = _compiled_circuit_details()
        state.circuit_loaded = True
        state.solution_available = False
        state.last_compiled_dss_file = resolved
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": False,
                **details,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as exc:
        _reset_failed_compile()
        return _err(str(exc))


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll); resets circuit_loaded, solution_available, and last compiled path."""
    try:
        engine.ensure_engine().text("ClearAll")
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
