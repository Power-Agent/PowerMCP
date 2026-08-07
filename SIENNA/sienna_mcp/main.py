"""SIENNA MCP server entry point (mirrors PSCAD/pscad_mcp/main.py's shape)."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from sienna_mcp.tools.compare_tools import register_compare_tools
from sienna_mcp.tools.solve_tools import register_solve_tools
from sienna_mcp.tools.system_tools import register_system_tools
from sienna_mcp.tools.translate_tools import register_translate_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sienna-mcp")


def create_server() -> FastMCP:
    """Factory to create and configure the FastMCP server.

    Registers each tool group from its own module (system/translate/solve/compare),
    matching PSCAD's modular register_*_tools(mcp) pattern.
    """
    mcp = FastMCP(
        "SIENNA",
        instructions=(
            "SIENNA MCP server: load Sienna PowerSystems.jl systems, translate them to "
            "PLEXOS via r2x, run PowerSimulations.jl solves via a local Julia install, and "
            "compare solutions. No PLEXOS license or vendor network call is required by this "
            "connector."
        ),
    )

    register_system_tools(mcp)
    register_translate_tools(mcp)
    register_solve_tools(mcp)
    register_compare_tools(mcp)

    logger.info("SIENNA MCP server initialized (load_system, translate_to_plexos, run_sienna_solve, compare_solutions).")
    return mcp


def main() -> None:
    """Main entry point."""
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
