"""The py_dss_interface DSS instance, built on first use.

Constructing ``DSS()`` loads the OpenDSS engine library, so it happens when a
tool is called rather than at import. The server then starts, and reports its
own capabilities, on a machine where the engine is missing or fails to load;
the failure reaches the caller as a tool result naming the cause.

The instance is a process-wide singleton because OpenDSS keeps one global
circuit: ``dss_tools`` is pointed at it once, and every tool shares that state.
"""

from __future__ import annotations

from typing import Any

_dss: Any = None


def get_dss() -> Any:
    """Return the shared DSS instance, building and wiring it on first call."""
    global _dss
    if _dss is None:
        from py_dss_interface import DSS
        from py_dss_toolkit import dss_tools

        instance = DSS()
        dss_tools.update_dss(instance)
        _dss = instance
    return _dss
