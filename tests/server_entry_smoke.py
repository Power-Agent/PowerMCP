"""Subprocess helper for importing one advertised server without its engine."""

from __future__ import annotations

import asyncio
import runpy
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


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
        class ModelData:
            pass

        _module("egret")
        _module("egret.data")
        _module("egret.data.model_data", ModelData=ModelData)
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
        class RawRead:
            pass

        _module("spicelib")
        _module("spicelib.raw")
        _module("spicelib.raw.raw_read", RawRead=RawRead)
    elif tool == "opendss":
        configuration = types.SimpleNamespace()
        dss_tools = types.SimpleNamespace(
            configuration=configuration,
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
    elif tool == "hope":
        try:
            __import__("yaml")
        except ImportError:
            _module(
                "yaml",
                safe_load=lambda _value: {},
                safe_dump=lambda *_args, **_kwargs: "",
            )


def main(tool_name: str) -> None:
    _stub_engines(tool_name)

    from mcp.server.mcpserver import MCPServer
    from powermcp import runner
    from powermcp.registry import get_tool

    calls = []
    real_run = MCPServer.run

    def record_run(self, *args, **kwargs):
        calls.append((self, args, kwargs))

    MCPServer.run = record_run
    try:
        tool = get_tool(tool_name)
        if tool.run_kind == "package":
            runner._launch_package(tool)
        elif tool.run_kind == "module":
            runner._launch_module(tool)
        else:
            runner._launch_script(tool)
    finally:
        MCPServer.run = real_run

    assert len(calls) == 1, f"{tool_name}: expected one run call, got {len(calls)}"
    server, _args, _kwargs = calls[0]
    tools = asyncio.run(server.list_tools())
    assert tools, f"{tool_name}: server registered no tools"


if __name__ == "__main__":
    main(sys.argv[1])
