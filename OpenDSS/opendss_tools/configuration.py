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


def compile_opendss_file(dss_file: str, force_recompile: bool = False) -> Dict[str, Any]:
    """Compile a master DSS file and verify the resulting circuit is usable.

    A successful return from the engine's compile command is not sufficient:
    OpenDSS can report redirect errors but leave a partial/empty circuit.
    The readiness payload is checked for explicit unsuccessful states and the
    active circuit is checked for a non-zero bus count when that count is
    exposed by the toolkit.
    """
    try:
        dss_file = checked_path(dss_file, purpose="dss_file")
        # A DSS model may Redirect/Compile sibling files. Preflight the whole
        # project tree when containment is enabled.
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
            readiness = dss_tools.configuration.circuit_readiness()
            validation_error = _validate_compiled_circuit(readiness)
            if validation_error:
                _reset_compile_state()
                return _err(validation_error)
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
        except Exception as exc:
            _reset_compile_state()
            return _err(f"Unable to verify the previously compiled circuit: {exc}")

    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness = dss_tools.configuration.circuit_readiness()
        validation_error = _validate_compiled_circuit(readiness)
        if validation_error:
            _reset_compile_state()
            return _err(validation_error)
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
    except Exception as exc:
        _reset_compile_state()
        return _err(str(exc))


def _validate_compiled_circuit(readiness: Any) -> str | None:
    """Return an error when readiness explicitly says compile is unsuccessful."""
    if isinstance(readiness, dict):
        for key in ("success", "ready", "is_ready", "circuit_ready", "converged"):
            value = readiness.get(key)
            if value is False:
                return f"OpenDSS circuit readiness reports {key}=false."
        for key in ("error", "errors", "compile_error", "redirect_errors"):
            value = readiness.get(key)
            if value:
                return f"OpenDSS circuit readiness reports {key}: {value}"
    # The compile operation can succeed while leaving an empty circuit. Use
    # the engine's bus count when the current toolkit version exposes it.
    try:
        bus_count = dss_tools.model._summary_model_records
        if callable(bus_count):
            bus_count = bus_count()
        if isinstance(bus_count, dict):
            counts = bus_count.get("counts", bus_count)
            if isinstance(counts, dict):
                buses = counts.get("buses", counts.get("bus_count"))
                if isinstance(buses, (int, float)) and buses <= 0:
                    return "OpenDSS compiled no buses; check Redirect/Compile paths and messages."
    except (AttributeError, TypeError, ValueError):
        # Not all py-dss-toolkit versions expose this metadata consistently;
        # do not fail a compile merely because optional metadata is unavailable.
        pass
    return None


def _reset_compile_state() -> None:
    state.circuit_loaded = False
    state.solution_available = False
    state.last_compiled_dss_file = None


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll); resets circuit state."""
    try:
        engine.ensure_engine().text("ClearAll")
        _reset_compile_state()
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as exc:
        return _err(str(exc))


def register_configuration_tools(mcp: FastMCP) -> None:
    mcp.tool()(compile_opendss_file)
    mcp.tool()(clear_all_opendss_memory)
