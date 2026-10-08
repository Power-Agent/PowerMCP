"""FastMCP factory: register all domain tools."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer as FastMCP

from core.engine import EngineUnavailable, ensure_engine
from opendss_tools.configuration import register_configuration_tools
from opendss_tools.interactive_view import register_interactive_view_tools
from opendss_tools.model import register_model_tools
from opendss_tools.results import register_results_tools
from opendss_tools.simulation import register_simulation_tools


def _engine_aware_mcp(mcp: FastMCP) -> FastMCP:
    """Make registered tools initialize OpenDSS only when they are called."""

    original_tool = mcp.tool

    def tool(*args: Any, **kwargs: Any):
        decorator = original_tool(*args, **kwargs)

        def register(fn: Callable[..., Any]):
            @wraps(fn)
            def guarded(*fn_args: Any, **fn_kwargs: Any):
                try:
                    ensure_engine()
                except EngineUnavailable as exc:
                    return {"success": False, "error": str(exc)}
                return fn(*fn_args, **fn_kwargs)

            return decorator(guarded)

        return register

    mcp.tool = tool  # type: ignore[method-assign]
    return mcp


def create_mcp() -> FastMCP:
    mcp = _engine_aware_mcp(FastMCP("PyDSS-MCP"))
    register_configuration_tools(mcp)
    register_model_tools(mcp)
    register_simulation_tools(mcp)
    register_results_tools(mcp)
    register_interactive_view_tools(mcp)
    return mcp
