"""Lazy py_dss_interface DSS instance and dss_tools wiring.

The vendor engine is intentionally not constructed at import time. Some
platforms can import py_dss_interface successfully but fail when the native
OpenDSS backend is constructed; doing that during module import prevents the
MCP server from completing initialize/list_tools.
"""

from __future__ import annotations

from py_dss_toolkit import dss_tools

dss = None
_engine_error: str | None = None


class EngineUnavailable(RuntimeError):
    """Raised when the OpenDSS backend cannot be initialized."""


def ensure_engine():
    """Initialize and return the shared DSS instance, once on demand."""
    global dss, _engine_error

    if dss is not None:
        return dss
    if _engine_error is not None:
        raise EngineUnavailable(_engine_error)

    try:
        from py_dss_interface import DSS

        candidate = DSS()
        dss_tools.update_dss(candidate)
        dss = candidate
        return dss
    except Exception as exc:
        dss = None
        _engine_error = (
            "OpenDSS engine initialization failed: "
            f"{type(exc).__name__}: {exc}. "
            "Check the py-dss-interface/OpenDSS installation and platform support."
        )
        raise EngineUnavailable(_engine_error) from exc
