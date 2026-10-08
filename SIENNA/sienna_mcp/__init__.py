"""sienna_mcp -- PowerMCP connector for Sienna (PowerSystems.jl / PowerSimulations.jl).

Exposes four tools over MCP: ``load_system``, ``translate_to_plexos``,
``run_sienna_solve``, ``compare_solutions``. Sienna itself is Julia-only (no PyPI
package); this connector drives it via a subprocess, the same mechanism the
sibling ``HOPE`` connector uses for its own Julia backend
(``HOPE/src/hope_mcp_server/core.py``). The PLEXOS-facing tools
(``translate_to_plexos``, ``compare_solutions``) call the upstream ``r2x``
package directly -- there is no PowerMCP-authored bridge/interop module.
"""

from __future__ import annotations

__all__ = ["main"]


def main() -> None:
    from .main import main as _main

    _main()
