"""Result helpers and precondition checks for the OpenDSS tools.

Every tool reports through the shape :mod:`powermcp.errors` names: tabular
data arrives under ``payload`` on a success, and a failure carries a message.
"""

from typing import Any, Dict, Optional

from core import state
from powermcp.errors import tool_error, tool_success


def _json_safe(obj: Any) -> Any:
    """Recursively convert numpy/pandas scalar-like values to native Python for JSON MCP payloads."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return _json_safe(obj.item())
        except Exception:
            pass
    return obj


def _ok(payload: Any = None) -> Dict[str, Any]:
    """Report a successful tool call, with any tabular data under ``payload``."""
    if payload is None:
        return tool_success()
    return tool_success(payload=_json_safe(payload))


def _err(msg: str) -> Dict[str, Any]:
    """Report a failed tool call."""
    return tool_error(msg)


def _require_circuit_loaded() -> Optional[Dict[str, Any]]:
    """Return an error result if no case has been compiled in this MCP session."""
    if not state.circuit_loaded:
        return _err("No circuit loaded; call compile_opendss_file first.")
    return None


def _require_solution() -> Optional[Dict[str, Any]]:
    """Return an error result if no snapshot solve has completed since compile/clear."""
    if not state.solution_available:
        return _err("No snapshot solution; call solve_opendss_snapshot first.")
    return None
