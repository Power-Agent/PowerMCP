"""`powermcp doctor` — check each tool's dependencies and configured paths.

Dependency checks use ``importlib.util.find_spec`` (which locates a module
without executing it) so the doctor never triggers a vendor engine's import-time
side effects (e.g. PSS/E ``psseinit``) and never crashes on a broken DLL. Vendor
engines that load from a captured directory (PSS/E, PSLF, PowerFactory) are not
import-probed at all — they are reported via their configured paths and verified
for real only at runtime.

Two checks are shared rather than per tool and print below the table: the MCP
SDK, which every server imports, and the configured roots used by servers that
call the shared filesystem policy. Both matter here because a server that fails
at launch gives its MCP client nothing at all — the diagnosis only exists in a
stderr the client does not read — so the doctor has to catch it beforehand.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from importlib.metadata import (
    PackageNotFoundError,
    packages_distributions,
    requires,
    version,
)

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import config as cfg
from .registry import Tool, all_tools, get_tool, install_hint
from .runner import probe_installed
from .sandbox import ALLOWED_ROOTS_ENV, LEGACY_ROOT_ENVS, allowed_roots

# Engines imported from a captured local dir (not from PyPI). Do not import-probe.
_PATH_LOADED = {"psse", "pslf", "powerfactory"}


def _surge_supported() -> bool:
    return (3, 12) <= sys.version_info[:2] < (3, 15)


def _canonical(name: str) -> str:
    """PEP 503 name, so `py_dss_toolkit` and `py-dss-toolkit` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _distributions(probe: str) -> list[str]:
    """Distributions providing the importable ``probe``.

    A probe is an import name and a requirement names a distribution; the two
    differ often enough to matter (`yaml` from PyYAML, `surge` from surge-py).
    Empty when nothing installed provides it, which is the missing case the
    caller has already reported.
    """
    top = probe.split(".")[0]
    return packages_distributions().get(top) or []


def _declared_requirement(probe: str) -> Requirement | None:
    """This project's own declared requirement on whatever provides ``probe``."""
    try:
        declared = requires("powermcp") or ()
    except PackageNotFoundError:
        return None
    provided = {_canonical(d) for d in _distributions(probe)}
    # Some wheels omit the top-level-name metadata used by
    # packages_distributions(). Exact import/distribution names still give us
    # an unambiguous fallback; the provider map handles names such as
    # ``yaml``/``PyYAML``.
    provided.add(_canonical(probe.split(".")[0]))
    for raw in declared:
        req = Requirement(raw)
        if _canonical(req.name) in provided and req.specifier:
            return req
    return None


def _version_status(probe: str) -> tuple[str, str] | None:
    """(style, message) when the installed version violates our requirement.

    ``find_spec`` answers "importable", which is a different question from "new
    enough": an old powerio imports fine and then refuses tools this repo calls.
    ``None`` when there is nothing to say — no declared floor, or it is met, or
    the installed version does not parse and there is nothing to compare.
    """
    req = _declared_requirement(probe)
    if req is None:
        return None
    try:
        installed = version(req.name)
        Version(installed)
    except (PackageNotFoundError, InvalidVersion):
        return None
    if req.specifier.contains(installed, prereleases=True):
        return None
    return "red", f"{req.name} {installed} does not satisfy {req.name}{req.specifier}"


def _dep_status(t: Tool) -> tuple[str, str]:
    """Return (style, message) for the dependency column."""
    if t.windows_only and sys.platform != "win32":
        return "dim", "skipped — Windows-only"
    if t.name == "surge" and not _surge_supported():
        return "yellow", f"needs Python 3.12–3.14 (have {sys.version_info.major}.{sys.version_info.minor})"
    if t.name in _PATH_LOADED:
        return "cyan", "vendor engine — loaded from configured path"
    if t.probe:
        if not probe_installed(t.probe):
            return "red", f"missing — {install_hint(t.extra)}"
        stale = _version_status(t.probe)
        if stale:
            return stale
    return "green", "ok"


def _sdk_status() -> tuple[str, str]:
    """Every server imports the MCP SDK, so no tool row would report it."""
    if not probe_installed("mcp"):
        return "red", f"mcp: missing — every server needs it; {install_hint(None)}"
    stale = _version_status("mcp")
    if stale:
        return stale
    return "green", f"mcp: {version('mcp')}"


def _containment_status() -> tuple[str, str]:
    """Whether model supplied paths are confined, and to what.

    Unset is a legitimate configuration, not a fault, but it is worth stating:
    a tool argument is whatever the model was persuaded to ask for.
    """
    roots = allowed_roots()
    if not roots:
        return "yellow", (
            f"MCP paths: unconfined — set {ALLOWED_ROOTS_ENV} to an "
            f"{os.pathsep!r} separated list of directories to confine reads and writes"
        )
    missing = [str(r) for r in roots if not r.is_dir()]
    if len(missing) == len(roots):
        return "red", (
            "MCP paths: every configured root is a directory that does not "
            "exist, so every path is refused: " + ", ".join(missing)
        )
    if missing:
        return "yellow", (
            "MCP paths: confined to "
            + ", ".join(str(r) for r in roots)
            + "; these do not exist and admit nothing: "
            + ", ".join(missing)
        )
    return "green", "MCP paths: confined to " + ", ".join(str(r) for r in roots)


def _path_status(t: Tool) -> tuple[str, str]:
    """Return (style, message) for the configured-paths column."""
    required = [ck for ck in t.config_keys if ck.required]
    optional = [ck for ck in t.config_keys if not ck.required]
    if not t.config_keys:
        return "dim", "—"
    missing = []
    wrong_type = []
    for ck in required:
        try:
            resolved = Path(cfg.get_path(t.name, ck.key))
        except cfg.ConfigError:
            missing.append(f"{t.name}.{ck.key}")
            continue
        valid = (
            resolved.is_dir() if ck.validate == "dir"
            else resolved.is_file() if ck.validate == "file"
            else resolved.exists()
        )
        if not valid:
            wrong_type.append(f"{t.name}.{ck.key} (expected {ck.validate}, got {resolved})")
    if missing or wrong_type:
        problems = []
        if missing:
            problems.append("set: " + ", ".join(missing))
        if wrong_type:
            problems.append("wrong type: " + ", ".join(wrong_type))
        return "yellow", "; ".join(problems)
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
        # escape(): a message carries user data such as `powermcp[andes]`, and
        # Rich reads a bracketed lowercase word as a style tag and drops it.
        table.add_row(
            t.name,
            f"[{dep_style}]{escape(dep_msg)}[/]",
            f"[{path_style}]{escape(path_msg)}[/]",
        )
        if t.external_solvers and not (t.windows_only and sys.platform != "win32"):
            solver_notes.append(f"  • {t.display}: needs {', '.join(t.external_solvers)} available at runtime")

    console = Console()
    console.print(table)
    for style, message in (_sdk_status(), _containment_status()):
        console.print(f"[{style}]{escape(message)}[/]")
    if solver_notes:
        console.print(
            "\n[dim]Note: some tools also need external solvers/runtimes on PATH "
            "(a green check above only means the Python package is present):[/]"
        )
        for note in solver_notes:
            console.print(f"[dim]{note}[/]")
    console.print(f"\n[dim]Config file: {cfg.config_path()}[/]")
