"""Launch a bundled MCP server by tool id.

``powermcp run <tool>`` resolves the tool via the registry and executes the
original, unmodified server file — so the same code keeps working when run
standalone from a checkout. Three launch styles (declared per tool in the
registry):

- ``script``: run the entry .py as ``__main__`` after temporarily putting
  the server dir on ``sys.path``.
- ``module``: put the module root on ``sys.path`` and run its package.
- ``package``: run a server shipped in its own distribution; no path changes.

All temporary import-path changes are restored when execution returns or
raises. This matters when PowerMCP is embedded in another Python process;
standalone CLI execution exits shortly afterwards, but tests and host
applications may continue importing modules.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys
import threading
from contextlib import contextmanager
from collections.abc import Iterator

from .registry import Tool, get_tool, install_hint


class LaunchError(RuntimeError):
    """Raised with an actionable message when a server cannot be launched."""


_SYS_PATH_LOCK = threading.RLock()


@contextmanager
def _temporary_sys_path(*paths: str) -> Iterator[None]:
    """Expose paths for one launch and restore the caller's import path.

    Restore the exact caller list contents in place, even if server startup
    reorders or mutates it. A finally block guarantees restoration when import
    or server startup raises.
    """
    # sys.path is process-global. Serialize PowerMCP launches so overlapping
    # contexts cannot restore snapshots over one another.
    with _SYS_PATH_LOCK:
        original = sys.path[:]
        try:
            for path in paths:
                if path not in sys.path:
                    sys.path.insert(0, path)
            yield
        finally:
            # Servers may reorder, remove, or append entries while importing.
            # Restore the caller's exact contents in place so references to the
            # sys.path list remain valid.
            sys.path[:] = original


def probe_installed(probe: str | None) -> bool:
    """True if ``probe`` resolves to a real (importable) module/package."""
    if not probe:
        return True
    try:
        spec = importlib.util.find_spec(probe)
    except Exception:
        return False
    return spec is not None and spec.origin is not None


def launch(name: str) -> None:
    tool = get_tool(name)
    _preflight(tool)
    if tool.run_kind == "package":
        _launch_package(tool)
    elif tool.run_kind == "module":
        _launch_module(tool)
    else:
        _launch_script(tool)


def _preflight(tool: Tool) -> None:
    if tool.windows_only and sys.platform != "win32":
        raise LaunchError(
            f"{tool.display} requires Windows-only software and cannot run on '{sys.platform}'."
        )
    if not probe_installed("mcp"):
        raise LaunchError(
            "The MCP SDK is not installed; every server needs it.\n"
            "  Install it with:  pip install powermcp"
        )
    if tool.probe and not probe_installed(tool.probe):
        raise LaunchError(
            f"{tool.display}: required package '{tool.probe.split('.')[0]}' is not installed.\n"
            f"  Install it with: {install_hint(tool.extra)}"
        )


def _launch_script(tool: Tool) -> None:
    script = tool.resolve_entry_script()
    server_dir = str(script.parent)
    with _temporary_sys_path(server_dir):
        runpy.run_path(str(script), run_name="__main__")


def _launch_module(tool: Tool) -> None:
    root = str(tool.resolve_module_root())
    with _temporary_sys_path(root):
        runpy.run_module(tool.module, run_name="__main__", alter_sys=True)


def _launch_package(tool: Tool) -> None:
    runpy.run_module(tool.module, run_name="__main__", alter_sys=True)
