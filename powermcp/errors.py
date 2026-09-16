"""One result shape for every PowerMCP tool.

A tool reports success as ``{"status": "success", ...}`` and failure as
``{"status": "error", "message": <text>}``, plus whatever result keys the tool
documents. A caller reads ``status`` once and handles either outcome the same
way against every bundled server.

:func:`run_tool` applies that shape to a tool body. A refused path or a
rejected argument becomes the message a caller can act on. Any other exception
is logged with its traceback and reported by type and text, so a failure
reaches the caller as a result rather than as an MCP protocol error, and the
traceback stays out of the JSON-RPC stream on stdout.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from powermcp.sandbox import PathNotAllowed

__all__ = ["run_tool", "tool_error", "tool_success"]


def tool_error(message: str, **fields: Any) -> dict[str, Any]:
    """Report a failed tool call.

    ``message`` is written for whoever called the tool. ``fields`` carries any
    additional key the tool documents on its failure branch, so a caller that
    reads a key after checking ``status`` finds it on every branch.
    """
    return {"status": "error", "message": message, **fields}


def tool_success(**fields: Any) -> dict[str, Any]:
    """Report a successful tool call and its result keys."""
    return {"status": "success", **fields}


def run_tool(call: Callable[[], dict], *, logger: logging.Logger) -> dict[str, Any]:
    """Run a tool body and report any failure through the error shape.

    ``PathNotAllowed`` and ``ValueError`` carry text already aimed at the
    caller, so their message passes through unchanged. Every other exception is
    logged through ``logger`` with its traceback and reported as
    ``"<ExceptionType>: <text>"``.
    """
    try:
        return call()
    except (PathNotAllowed, ValueError) as exc:
        return tool_error(str(exc))
    except Exception as exc:  # noqa: BLE001 - every failure leaves as a result
        logger.exception("Tool call failed")
        return tool_error(f"{type(exc).__name__}: {exc}")
