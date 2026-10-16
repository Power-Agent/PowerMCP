"""FastMCP factory: register all domain tools."""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer as FastMCP

from core.engine import EngineUnavailable, ensure_engine
from opendss_tools.configuration import register_configuration_tools
from opendss_tools.interactive_view import register_interactive_view_tools
from opendss_tools.model import register_model_tools
from opendss_tools.results import register_results_tools
from opendss_tools.simulation import register_simulation_tools
from utils.responses import _err


def _engine_aware_mcp(mcp: FastMCP) -> FastMCP:
    """Make registered tools initialize OpenDSS only when they are called."""

    original_tool = mcp.tool

    def tool(*args: Any, **kwargs: Any):
        decorator = original_tool(*args, **kwargs)

        def register(fn: Callable[..., Any]):
            if inspect.iscoroutinefunction(fn):
                @wraps(fn)
                async def guarded(*fn_args: Any, **fn_kwargs: Any):
                    try:
                        ensure_engine()
                    except EngineUnavailable as exc:
                        return _err(str(exc))
                    return await fn(*fn_args, **fn_kwargs)
            else:
                @wraps(fn)
                def guarded(*fn_args: Any, **fn_kwargs: Any):
                    try:
                        ensure_engine()
                    except EngineUnavailable as exc:
                        return _err(str(exc))
                    return fn(*fn_args, **fn_kwargs)

            return decorator(guarded)

        return register

    # This guard covers tools registered via mcp.tool(). Tools registered via
    # mcp.add_tool() bypass lazy initialization and must be wrapped explicitly.
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
