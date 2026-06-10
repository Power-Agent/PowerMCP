"""The PowerMCP tool registry — the single source of truth for every server.

Everything else (CLI, runner, wizard, doctor, client-config writers) reads tool
metadata from here: how to launch each server, which pip extra provides it,
whether it is Windows-only, and which local software paths it needs captured in
``~/.powermcp/config.toml``.
"""

from __future__ import annotations

import importlib.resources as resources
from dataclasses import dataclass, field
from pathlib import Path

# In an editable install or a raw git checkout, the powermcp package lives at
# <repo>/powermcp, so its parent is the repo root that holds PSSE/, pandapower/...
# In an installed wheel the server dirs live under powermcp/_servers/ instead
# (see resolve_server_dir).
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ConfigKey:
    """A local software path a tool needs captured at install time."""

    key: str  # stored as [tool].<key> in config.toml
    prompt: str  # shown by the install wizard
    validate: str = "dir"  # "dir" | "file" | "any"
    required: bool = True
    legacy_default: str | None = None  # historical hardcoded path, used as last resort


@dataclass(frozen=True)
class Tool:
    """A single MCP server bundled in the distribution."""

    name: str  # CLI id: `powermcp run <name>`
    display: str
    kind: str  # "open-source" | "closed-source"
    windows_only: bool
    extra: str | None  # pip extra that installs it; None for core (pandapower/pypsa)
    server_dir: str  # top-level dir name, e.g. "PSSE"
    run_kind: str  # "script" | "module"
    entry_rel: str | None = None  # for run_kind=="script": path under server_dir
    module: str | None = None  # for run_kind=="module": dotted module run with -m
    module_root_rel: str | None = None  # dir (under server_dir) to add to sys.path for the module
    probe: str | None = None  # importable linchpin dependency, for doctor
    config_keys: tuple[ConfigKey, ...] = field(default_factory=tuple)
    external_solvers: tuple[str, ...] = field(default_factory=tuple)  # informational
    notes: str = ""

    # -- path resolution --------------------------------------------------- #
    def resolve_server_dir(self) -> Path:
        """Return the on-disk server directory, working in all three layouts:
        installed wheel (powermcp/_servers/<dir>), editable install, raw checkout."""
        # 1) installed wheel: shipped under the package as powermcp/_servers/<dir>
        try:
            packaged = Path(str(resources.files("powermcp"))) / "_servers" / self.server_dir
            if packaged.exists():
                return packaged
        except (ModuleNotFoundError, TypeError, OSError):
            pass
        # 2) editable install / raw checkout: <repo>/<dir>
        checkout = REPO_ROOT / self.server_dir
        if checkout.exists():
            return checkout
        raise FileNotFoundError(
            f"Cannot locate server directory '{self.server_dir}' for tool '{self.name}'. "
            f"Looked under the installed package and at {checkout}."
        )

    def resolve_entry_script(self) -> Path:
        if self.run_kind != "script" or not self.entry_rel:
            raise ValueError(f"{self.name} is not a script-launched tool")
        return self.resolve_server_dir() / self.entry_rel

    def resolve_module_root(self) -> Path:
        base = self.resolve_server_dir()
        return base / self.module_root_rel if self.module_root_rel else base


# Tools whose path is genuinely Windows-only commercial software.
_W = True

TOOLS: dict[str, "Tool"] = {
    t.name: t
    for t in (
        # ---- CORE (always installed) ----
        Tool(
            "pandapower", "pandapower", "open-source", windows_only=False, extra=None,
            server_dir="pandapower", run_kind="script", entry_rel="panda_mcp.py",
            probe="pandapower",
        ),
        Tool(
            "pypsa", "PyPSA", "open-source", windows_only=False, extra=None,
            server_dir="PyPSA", run_kind="script", entry_rel="pypsa_mcp.py",
            probe="pypsa", external_solvers=("HiGHS", "CBC", "GLPK", "Gurobi"),
        ),
        # ---- OPEN-SOURCE EXTRAS ----
        Tool(
            "andes", "ANDES", "open-source", windows_only=False, extra="andes",
            server_dir="ANDES", run_kind="script", entry_rel="andes_mcp.py",
            probe="andes",
        ),
        Tool(
            "egret", "Egret", "open-source", windows_only=False, extra="egret",
            server_dir="Egret", run_kind="script", entry_rel="egret_mcp.py",
            probe="egret", external_solvers=("ipopt", "Gurobi"),
        ),
        Tool(
            "surge", "surge", "open-source", windows_only=False, extra="surge",
            server_dir="surge", run_kind="script", entry_rel="surge_mcp.py",
            probe="surge", external_solvers=("HiGHS", "Ipopt"),
            notes="Requires Python 3.12-3.14 (pyo3/maturin).",
        ),
        Tool(
            "opendss", "OpenDSS", "open-source", windows_only=False, extra="opendss",
            server_dir="OpenDSS", run_kind="script", entry_rel="opendss_mcp.py",
            probe="py_dss_toolkit",
        ),
        Tool(
            "hope", "HOPE", "open-source", windows_only=False, extra="hope",
            server_dir="HOPE", run_kind="module",
            module="hope_mcp_server", module_root_rel="src",
            probe="yaml",
            config_keys=(
                ConfigKey("repo_root", "Path to the HOPE git repository root", "dir"),
                ConfigKey("julia_bin", "Path to the Julia executable", "file"),
                ConfigKey("julia_depot_path", "JULIA_DEPOT_PATH (optional, Enter to skip)", "dir", required=False),
            ),
            external_solvers=("Julia",),
        ),
        Tool(
            "powerio", "PowerIO", "open-source", windows_only=False, extra="powerio",
            server_dir="powerio", run_kind="script", entry_rel="powerio_mcp.py",
            probe="powerio",
            notes="Format-neutral case conversion and matrix builder; the JSON transport is the cross-server exchange format.",
        ),
        # ---- CLOSED-SOURCE / VENDOR ----
        Tool(
            "powerworld", "PowerWorld", "closed-source", windows_only=_W, extra="powerworld",
            server_dir="PowerWorld", run_kind="script", entry_rel="powerworld_mcp.py",
            probe="esa",
            notes="esa (Easy SimAuto) auto-discovers a running, licensed PowerWorld Simulator via COM; no path to capture.",
        ),
        Tool(
            "psse", "PSS/E", "closed-source", windows_only=_W, extra="psse",
            server_dir="PSSE", run_kind="script", entry_rel="psse_mcp.py",
            probe=None,  # psspy loads from a captured path, not pip; checked at runtime
            config_keys=(
                ConfigKey(
                    "python_lib", r"Path to the PSSE PSSPYxxx dir (e.g. ...\PSSE36\36.2\PSSPY311)",
                    "dir", legacy_default=r"C:\Program Files\PTI\PSSE36\36.2\PSSPY311",
                ),
                ConfigKey(
                    "bin", r"Path to the PSSE PSSBIN dir",
                    "dir", legacy_default=r"C:\Program Files\PTI\PSSE36\36.2\PSSBIN",
                ),
                ConfigKey("version", "PSSE version string, e.g. 36.2 (optional)", "any", required=False),
            ),
        ),
        Tool(
            "pslf", "PSLF", "closed-source", windows_only=_W, extra="pslf",
            server_dir="PSLF", run_kind="script", entry_rel="pslf_mcp.py",
            probe=None,  # PSLF_PYTHON is vendor-supplied, not importable until path injected
            config_keys=(
                ConfigKey("python_lib", "Directory containing the PSLF_PYTHON module", "dir"),
            ),
        ),
        Tool(
            "powerfactory", "PowerFactory", "closed-source", windows_only=_W, extra="powerfactory",
            server_dir="PowerFactory", run_kind="script", entry_rel="MCP_PowerFactory.py",
            probe="fastmcp",
            config_keys=(
                ConfigKey(
                    "python_path",
                    r"Path to PowerFactory's bundled Python dir (e.g. ...\DIgSILENT\PowerFactory 2024\Python\3.11)",
                    "dir",
                ),
                ConfigKey(
                    "config_path", "Path to simulation_config.json (optional; defaults to ~/.powermcp/powerfactory/)",
                    "file", required=False,
                ),
            ),
        ),
        Tool(
            "pscad", "PSCAD", "closed-source", windows_only=_W, extra="pscad-windows",
            server_dir="PSCAD", run_kind="module",
            module="pscad_mcp.main", module_root_rel=None,  # parent of pscad_mcp is the server dir itself
            probe="mhi.pscad",
            notes="mhi-pscad/mhi-psout come from the `pscad-windows` extra; PSCAD must be installed.",
        ),
        Tool(
            "ltspice", "LTSpice", "closed-source", windows_only=False, extra="ltspice",
            server_dir="LTSpice", run_kind="script", entry_rel="ltspice_mcp.py",
            probe="PyLTSpice",
            config_keys=(
                ConfigKey(
                    "exe", r"Path to the LTspice executable (e.g. ...\LTspiceXVII\XVIIx64.exe)",
                    "file", legacy_default=r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
                ),
            ),
        ),
    )
}

# Tools installed by a bare `pip install powermcp` and pre-checked in the wizard.
CORE: tuple[str, ...] = ("pandapower", "pypsa")


def get_tool(name: str) -> "Tool":
    try:
        return TOOLS[name]
    except KeyError:
        raise KeyError(f"unknown tool '{name}'. Known tools: {', '.join(TOOLS)}") from None


def all_tools() -> list["Tool"]:
    return list(TOOLS.values())


def legacy_default(tool: str, key: str) -> str | None:
    """Return the historical hardcoded path for a tool/key, if any."""
    t = TOOLS.get(tool)
    if not t:
        return None
    for ck in t.config_keys:
        if ck.key == key:
            return ck.legacy_default
    return None
