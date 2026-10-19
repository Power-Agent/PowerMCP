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

    OpenDSS may report a failed Redirect/Compile in diagnostics yet leave a
    partial circuit. A successful return from the wrapper therefore must also
    pass readiness and model-integrity checks before this session marks the
    circuit as loaded.
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
    """Return an error when engine readiness or model counts reject the circuit."""
    if isinstance(readiness, dict):
        for key in ("success", "ready", "is_ready", "circuit_ready", "converged"):
            value = readiness.get(key)
            if value is False:
                return f"OpenDSS circuit readiness reports {key}=false."
        for key in ("error", "errors", "compile_error", "redirect_errors"):
            value = readiness.get(key)
            if value:
                return f"OpenDSS circuit readiness reports {key}: {value}"

    # The 13-bus failure mode leaves a compile command without the expected
    # model. Inspect summary records only when this toolkit version exposes a
    # bus count, keeping compatibility with versions that return other shapes.
    try:
        summary = dss_tools.model._summary_model_records
        if callable(summary):
            summary = summary()
        if isinstance(summary, dict):
            counts = summary.get("counts", summary)
            if isinstance(counts, dict):
                buses = counts.get("buses", counts.get("bus_count"))
                if isinstance(buses, (int, float)) and buses <= 0:
                    return "OpenDSS compiled no buses; check Redirect/Compile paths and engine diagnostics."
    except (AttributeError, TypeError, ValueError):
        # Optional metadata varies by toolkit version; don't reject a circuit
        # solely because this extra diagnostic is unavailable.
        pass
    return None


def _reset_compile_state() -> None:
    state.circuit_loaded = False
    state.solution_available = False
    state.last_compiled_dss_file = None


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory and reset circuit state."""
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
