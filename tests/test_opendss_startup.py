"""Regression tests for lazy OpenDSS backend initialization."""

from __future__ import annotations

import asyncio
import importlib
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor

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
        "core.engine", "core.server", "core",
        "opendss_tools.configuration", "opendss_tools.interactive_view",
        "opendss_tools.model", "opendss_tools.results", "opendss_tools.simulation",
        "opendss_tools", "utils.responses", "utils",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

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

def test_engine_is_initialized_once_and_reused(monkeypatch):
    calls = []
    updates = []

    class FakeDSS:
        pass

    def fake_dss():
        calls.append("construct")
        return FakeDSS()

    server = _load_server(monkeypatch, dss_factory=fake_dss)
    engine = importlib.import_module("core.engine")
    engine.dss_tools.update_dss = lambda instance: updates.append(instance)

    first = engine.ensure_engine()
    second = engine.ensure_engine()

    assert first is second
    assert len(calls) == 1
    assert updates == [first]


def test_engine_failure_message_requires_restart(monkeypatch):
    def fake_dss():
        raise RuntimeError("transient native error")

    _load_server(monkeypatch, dss_factory=fake_dss)
    engine = importlib.import_module("core.engine")
    with pytest.raises(engine.EngineUnavailable, match="restart the MCP server"):
        engine.ensure_engine()


def test_concurrent_engine_requests_construct_and_wire_once(monkeypatch):
    calls = []
    updates = []

    class FakeDSS:
        pass

    def fake_dss():
        time.sleep(0.02)  # release the GIL so concurrent callers overlap at startup
        instance = FakeDSS()
        calls.append(instance)
        return instance

    _load_server(monkeypatch, dss_factory=fake_dss)
    engine = importlib.import_module("core.engine")
    engine.dss_tools.update_dss = lambda instance: updates.append(instance)

    with ThreadPoolExecutor(max_workers=8) as pool:
        instances = list(pool.map(lambda _index: engine.ensure_engine(), range(16)))

    assert len(calls) == 1
    assert len(updates) == 1
    assert all(instance is calls[0] for instance in instances)
