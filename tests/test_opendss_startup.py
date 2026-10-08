"""Regression tests for lazy OpenDSS backend initialization."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types

import pytest


def _load_server(monkeypatch, *, dss_factory):
    opendss_dir = __import__("pathlib").Path(__file__).resolve().parents[1] / "OpenDSS"
    monkeypatch.syspath_prepend(str(opendss_dir))

    fake_tools = types.SimpleNamespace(
        update_dss=lambda _dss: None,
        configuration=types.SimpleNamespace(),
        model=types.SimpleNamespace(),
        simulation=types.SimpleNamespace(),
        results=types.SimpleNamespace(),
        interactive_view=types.SimpleNamespace(),
    )
    monkeypatch.setitem(sys.modules, "py_dss_toolkit", types.SimpleNamespace(dss_tools=fake_tools))
    monkeypatch.setitem(sys.modules, "py_dss_interface", types.SimpleNamespace(DSS=dss_factory))

    for name in (
        "core.engine", "core.server", "opendss_tools.configuration",
        "opendss_tools.interactive_view", "opendss_tools.model",
        "opendss_tools.results", "opendss_tools.simulation", "utils.responses",
    ):
        sys.modules.pop(name, None)

    return importlib.import_module("core.server")


def test_server_creation_does_not_initialize_dss(monkeypatch):
    calls = []

    def fake_dss():
        calls.append("constructed")
        raise RuntimeError("native backend unavailable")

    server = _load_server(monkeypatch, dss_factory=fake_dss)
    mcp = server.create_mcp()

    assert calls == []
    tools = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert "compile_opendss_file" in tools
    assert "solve_snapshot" in tools


def test_engine_failure_becomes_structured_tool_error(monkeypatch):
    def fake_dss():
        raise AttributeError("native backend unavailable")

    server = _load_server(monkeypatch, dss_factory=fake_dss)
    mcp = server.create_mcp()

    def operation():
        return {"success": True}

    guarded = mcp.tool()(operation)
    result = guarded()

    assert result["success"] is False
    assert "OpenDSS engine initialization failed" in result["error"]


def test_toolkit_wiring_failure_does_not_cache_partial_engine(monkeypatch):
    class FakeDSS:
        pass

    _load_server(monkeypatch, dss_factory=FakeDSS)
    engine = importlib.import_module("core.engine")

    def fail_update(_dss):
        raise RuntimeError("toolkit wiring unavailable")

    engine.dss_tools.update_dss = fail_update

    with pytest.raises(engine.EngineUnavailable, match="toolkit wiring unavailable"):
        engine.ensure_engine()

    assert engine.dss is None