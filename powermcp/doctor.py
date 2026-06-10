"""`powermcp doctor` — check each tool's dependencies and configured paths.

Dependency checks use ``importlib.util.find_spec`` (which locates a module
without executing it) so the doctor never triggers a vendor engine's import-time
side effects (e.g. PSS/E ``psseinit``) and never crashes on a broken DLL. Vendor
engines that load from a captured directory (PSS/E, PSLF, PowerFactory) are not
import-probed at all — they are reported via their configured paths and verified
for real only at runtime.
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from . import config as cfg
from .registry import Tool, all_tools, get_tool
from .runner import probe_installed

# Engines imported from a captured local dir (not from PyPI). Do not import-probe.
_PATH_LOADED = {"psse", "pslf", "powerfactory"}


def _surge_supported() -> bool:
    return (3, 12) <= sys.version_info[:2] < (3, 15)


def _dep_status(t: Tool) -> tuple[str, str]:
    """Return (style, message) for the dependency column."""
    if t.windows_only and sys.platform != "win32":
        return "dim", "skipped — Windows-only"
    if t.name == "surge" and not _surge_supported():
        return "yellow", f"needs Python 3.12–3.14 (have {sys.version_info.major}.{sys.version_info.minor})"
    if t.name in _PATH_LOADED:
        return "cyan", "vendor engine — loaded from configured path"
    if t.probe:
        if probe_installed(t.probe):
            return "green", "ok"
        return "red", f"missing — pip install powermcp[{t.extra}]"
    return "green", "ok"


def _path_status(t: Tool) -> tuple[str, str]:
    """Return (style, message) for the configured-paths column."""
    required = [ck for ck in t.config_keys if ck.required]
    optional = [ck for ck in t.config_keys if not ck.required]
    if not t.config_keys:
        return "dim", "—"
    missing = []
    for ck in required:
        try:
            cfg.get_path(t.name, ck.key)
        except cfg.ConfigError:
            missing.append(f"{t.name}.{ck.key}")
    if missing:
        return "yellow", "set: " + ", ".join(missing)
    label = "configured"
    if optional:
        label += f" ({len(optional)} optional)"
    return "green", label


def run_doctor(tool: str | None = None) -> None:
    tools = [get_tool(tool)] if tool else all_tools()
    table = Table(title="PowerMCP doctor")
    table.add_column("tool")
    table.add_column("dependencies")
    table.add_column("config paths")
    solver_notes: list[str] = []
    for t in tools:
        dep_style, dep_msg = _dep_status(t)
        path_style, path_msg = _path_status(t)
        table.add_row(t.name, f"[{dep_style}]{dep_msg}[/]", f"[{path_style}]{path_msg}[/]")
        if t.external_solvers and not (t.windows_only and sys.platform != "win32"):
            solver_notes.append(f"  • {t.display}: needs {', '.join(t.external_solvers)} available at runtime")

    console = Console()
    console.print(table)
    if solver_notes:
        console.print(
            "\n[dim]Note: some tools also need external solvers/runtimes on PATH "
            "(a green check above only means the Python package is present):[/]"
        )
        for note in solver_notes:
            console.print(f"[dim]{note}[/]")
    console.print(f"\n[dim]Config file: {cfg.config_path()}[/]")
