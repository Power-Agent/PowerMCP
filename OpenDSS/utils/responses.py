"""JSON response helpers and precondition guards."""

from typing import Any, Dict, Optional

from core import state


def _ok(payload: Any = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    if payload is not None:
        out["payload"] = payload
    return out


def _err(msg: str) -> Dict[str, Any]:
    return {"success": False, "error": msg}


def _require_circuit_loaded() -> Optional[Dict[str, Any]]:
    """Return an error response if no case has been compiled in this MCP session."""
    if not state.circuit_loaded:
        return _err("No circuit loaded; call compile_opendss_file first.")
    return None


def _require_solution() -> Optional[Dict[str, Any]]:
    """Return an error response if no snapshot solve has completed since compile/clear."""
    if not state.solution_available:
        return _err("No snapshot solution; call solve_opendss_snapshot first.")
    return None
