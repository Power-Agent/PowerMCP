"""Launch a bundled MCP server by tool id.

``powermcp run <tool>`` resolves the tool via the registry and executes the
original, unmodified server file — so the same code keeps working when run
standalone from a checkout. Three launch styles (declared per tool in the
registry):

- ``script``: run the entry .py as ``__main__`` (its own ``mcp.run(...)`` fires),
  after putting the server dir and its parent on ``sys.path`` so existing
  relative imports (PyPSA's ``sys.path.append`` parent, OpenDSS's
  ``from core.server import ...``) resolve exactly as in standalone use.
- ``module``: put the module root on ``sys.path`` and ``runpy.run_module`` the
  package's ``__main__`` (PSCAD's ``pscad_mcp.main``, HOPE's ``hope_mcp_server``).
- ``package``: ``runpy.run_module`` a server that ships in its own distribution
  and is already importable (powerio's ``powerio.mcp``). Nothing goes on
  ``sys.path`` and this repo bundles no copy of that server.
"""

from __future__ import annotations

import importlib.util
import runpy
import sys

from .registry import Tool, get_tool, install_hint


class LaunchError(RuntimeError):
    """Raised with an actionable message when a server cannot be launched."""


def probe_installed(probe: str | None) -> bool:
    """True if ``probe`` resolves to a real (importable) module/package.

    Uses find_spec on the FULL dotted name (no module execution). Two cases this
    must get right:
    - ``surge`` (top-level): the repo's ``surge/`` folder is a PEP 420 namespace
      portion (origin None) and must NOT be mistaken for the installed library —
      so we require a real ``origin``.
    - ``mhi.pscad`` (subpackage of a namespace): ``mhi`` itself is a namespace
      package shared by the ``mhi-pscad``/``mhi-psout`` distributions, so probing
      the top-level ``mhi`` would wrongly look "missing". Probing the full
      ``mhi.pscad`` resolves the real subpackage (which has an origin).
    """
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
    # Every server imports the MCP SDK at module scope, so without this the
    # failure is a raw ImportError traceback rather than an actionable message.
    if not probe_installed("mcp"):
        raise LaunchError(
            "The MCP SDK is not installed; every server needs it.\n"
            "  Install it with:  pip install powermcp"
        )
    # Only probe pip-provided linchpins. Vendor engines (PSS/E psspy, PSLF) have
    # probe=None: they live behind a captured path and report their own
    # actionable error from the server's lazy init.
    if tool.probe and not probe_installed(tool.probe):
        raise LaunchError(
            f"{tool.display}: required package '{tool.probe.split('.')[0]}' is not installed.\n"
            f"  Install it with:  {install_hint(tool.extra)}"
        )


def _launch_script(tool: Tool) -> None:
    script = tool.resolve_entry_script()
    # Emulate `python <script>`: only the script's own directory goes on sys.path
    # (runpy.run_path does not add it). We deliberately do NOT add the parent —
    # the parent holds dirs named exactly like libraries (pandapower/, surge/),
    # and each server temporarily exposes the repo root only while importing
    # shared powermcp modules (OpenDSS also inserts its root for `core`).
    server_dir = str(script.parent)
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    runpy.run_path(str(script), run_name="__main__")


def _launch_module(tool: Tool) -> None:
    root = str(tool.resolve_module_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    runpy.run_module(tool.module, run_name="__main__", alter_sys=True)


def _launch_package(tool: Tool) -> None:
    # The server is a dependency, already on sys.path wherever pip put it, so
    # there is no directory to resolve and nothing of ours to shadow it with.
    runpy.run_module(tool.module, run_name="__main__", alter_sys=True)
