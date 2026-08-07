"""``load_system`` -- load a Sienna PSY-JSON system and summarize it.

Uses ``r2x_core.System.from_json`` (part of the ``r2x`` distribution on PyPI)
directly. ``r2x_core.System`` deserializes the same infrasys-based JSON schema
that PowerSystems.jl's own ``to_json``/``from_json`` produce, so this accepts:

* a PSY JSON file exported natively from Sienna (Julia side), or
* a PSY JSON file produced by the sibling ``PLEXOSDB`` connector's
  ``translate_to_sienna`` tool (see ``PLEXOSDB`` / GitHub issue #53 -- out of
  scope for this connector, mentioned here only as a compatible input source).

The ``r2x`` import is deferred to call time (not module import time) so that
importing ``sienna_mcp.main`` never requires ``r2x`` to be installed -- see
``tests/test_vendor_import.py`` (``test_sienna_main_import_and_server_creation_are_r2x_free``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

R2X_NOT_INSTALLED_MESSAGE = (
    "r2x is not installed. Install the 'sienna' extra "
    "(`pip install powermcp[sienna]`) or `pip install r2x` directly."
)


def _component_counts(system: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for component_type in system.get_component_types():
        name = getattr(component_type, "__name__", str(component_type))
        counts[name] = len(list(system.get_components(component_type)))
    return counts


def load_system(psy_json_path: str) -> dict[str, Any]:
    """Load a Sienna PSY-JSON system file and return a component-count summary.

    Does not return the full system (systems can be large); use the returned
    ``component_counts`` to decide what to inspect further, or pass
    ``psy_json_path`` straight through to ``translate_to_plexos``.
    """
    try:
        from r2x_core import System
    except ImportError:
        return {
            "ok": False,
            "error_type": "r2x_not_installed",
            "message": R2X_NOT_INSTALLED_MESSAGE,
        }

    path = Path(psy_json_path).expanduser()
    if not path.is_file():
        return {
            "ok": False,
            "error_type": "file_not_found",
            "message": f"PSY JSON file not found: {path}",
            "path": str(path),
        }

    try:
        system = System.from_json(path)
    except Exception as exc:  # r2x/infrasys raise a variety of errors on bad input
        return {
            "ok": False,
            "error_type": "load_failed",
            "message": f"Failed to load system from {path}: {exc}",
            "path": str(path),
        }

    component_counts = _component_counts(system)
    return {
        "ok": True,
        "path": str(path),
        "name": getattr(system, "name", None),
        "description": getattr(system, "description", None),
        "component_type_count": len(component_counts),
        "component_counts": component_counts,
        "total_components": sum(component_counts.values()),
    }


def register_system_tools(mcp: FastMCP) -> None:
    """Register system-loading tools with the MCP server."""
    mcp.tool(
        name="load_system",
        description=(
            "Load a Sienna PowerSystems.jl system from a PSY JSON file (produced by "
            "PowerSystems.jl's to_json on the Julia side, or by the PLEXOSDB connector's "
            "translate_to_sienna tool, see issue #53) and return a component-type-count "
            "summary. Calls r2x's r2x_core.System.from_json directly."
        ),
    )(load_system)
