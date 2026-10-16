"""Run a bundled entrypoint as if PowerMCP were an uninstalled git clone."""

from __future__ import annotations

import asyncio
import importlib.abc
import runpy
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    sys.modules[name] = module
    if "." in name:
        parent_name, child_name = name.rsplit(".", 1)
        parent = sys.modules.setdefault(parent_name, types.ModuleType(parent_name))
        if not hasattr(parent, "__path__"):
            parent.__path__ = []
        setattr(parent, child_name, module)
    return module


def _stub_engines(tool: str) -> None:
    if tool == "andes":
        _module("andes", config_logger=lambda **_kwargs: None)
    elif tool == "egret":
        _module("egret")
        _module("egret.data")
        _module("egret.data.model_data", ModelData=type("ModelData", (), {}))
        _module("egret.models")
        _module("egret.models.unit_commitment", solve_unit_commitment=lambda *_a, **_k: None)
        _module(
            "egret.models.acopf",
            solve_acopf=lambda *_a, **_k: None,
            create_psv_acopf_model=object(),
        )
        _module(
            "egret.models.dcopf",
            solve_dcopf=lambda *_a, **_k: None,
            create_ptdf_dcopf_model=object(),
        )
    elif tool == "surge":
        _module("surge", Network=type("Network", (), {}))
    elif tool == "ltspice":
        _module("spicelib")
        _module("spicelib.raw")
        _module("spicelib.raw.raw_read", RawRead=type("RawRead", (), {}))
    elif tool == "opendss":
        dss_tools = types.SimpleNamespace(
            configuration=types.SimpleNamespace(),
            update_dss=lambda _dss: None,
        )
        _module("py_dss_toolkit", dss_tools=dss_tools)
        _module("py_dss_interface", DSS=lambda: object())
    elif tool == "powerworld":
        class PowerWorldError(Exception):
            pass

        _module("esa", SAW=type("SAW", (), {}), PowerWorldError=PowerWorldError)
    elif tool == "pscad":
        _module("psutil", process_iter=lambda *_args, **_kwargs: [])
    elif tool == "plexosdb":
        # The bundled PLEXOSDB server re-exports the git-only upstream
        # plexosdb-mcp package; stand in for it with a real MCPServer so the
        # two locally-defined tools still register.
        from mcp.server.mcpserver import MCPServer

        _module(
            "plexosdb_mcp.server",
            MCPServerState=type("MCPServerState", (), {}),
            build_mcp_server=lambda: MCPServer("plexosdb"),
            main=lambda *_args, **_kwargs: None,
        )


class _RequireCloneBootstrap(importlib.abc.MetaPathFinder):
    """Hide the editable install until an entrypoint exposes the repo root."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "powermcp" and str(REPO) not in sys.path:
            raise ModuleNotFoundError(
                "powermcp is unavailable until the clone entrypoint bootstraps it"
            )
        return None


def main(tool: str, relative_script: str, expect_run: bool = True) -> None:
    script = REPO / relative_script
    _stub_engines(tool)

    from mcp.server.mcpserver import MCPServer

    calls = []
    real_run = MCPServer.run
    MCPServer.run = lambda self, *args, **kwargs: calls.append((self, args, kwargs))
    sys.meta_path.insert(0, _RequireCloneBootstrap())
    sys.path[:] = [
        str(script.parent),
        *(entry for entry in sys.path if Path(entry or ".").resolve() != REPO),
    ]
    for name in tuple(sys.modules):
        if name == "powermcp" or name.startswith("powermcp."):
            del sys.modules[name]
    try:
        runpy.run_path(str(script), run_name="__main__" if expect_run else "clone_smoke")
    finally:
        MCPServer.run = real_run

    if not expect_run:
        return
    assert len(calls) == 1, f"{tool}: expected one run call, got {len(calls)}"
    tools = asyncio.run(calls[0][0].list_tools())
    assert tools, f"{tool}: server registered no tools"


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] != ["import-only"])
