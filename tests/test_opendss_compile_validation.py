"""Regression tests for OpenDSS compile-result validation."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture()
def configuration_module(monkeypatch):
    opendss_dir = Path(__file__).resolve().parents[1] / "OpenDSS"
    monkeypatch.syspath_prepend(str(opendss_dir))

    fake_config = types.SimpleNamespace(
        compile_dss=lambda _path: None,
        circuit_readiness=lambda: {"ready": True},
    )
    fake_model = types.SimpleNamespace(
        _summary_model_records={"counts": {"buses": 13}}
    )
    fake_tools = types.SimpleNamespace(
        configuration=fake_config,
        model=fake_model,
        update_dss=lambda _dss: None,
    )
    monkeypatch.setitem(
        sys.modules, "py_dss_toolkit", types.SimpleNamespace(dss_tools=fake_tools)
    )
    monkeypatch.setitem(
        sys.modules,
        "powermcp.sandbox",
        types.SimpleNamespace(
            PathNotAllowed=type("PathNotAllowed", (Exception,), {}),
            allowed_roots=lambda: [],
            checked_path=lambda value, **_kwargs: str(value),
            checked_read_tree=lambda *_args, **_kwargs: None,
        ),
    )

    for name in (
        "core", "core.state", "core.engine", "opendss_tools",
        "opendss_tools.configuration", "utils", "utils.responses",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    state = types.ModuleType("core.state")
    state.circuit_loaded = False
    state.solution_available = False
    state.last_compiled_dss_file = None
    monkeypatch.setitem(sys.modules, "core.state", state)

    engine = types.ModuleType("core.engine")
    engine.ensure_engine = lambda: types.SimpleNamespace(text=lambda _cmd: None)
    monkeypatch.setitem(sys.modules, "core.engine", engine)

    responses = types.ModuleType("utils.responses")
    responses._err = lambda message: {"success": False, "error": message}
    responses._ok = lambda payload=None: {"success": True, **({"payload": payload} if payload is not None else {})}
    monkeypatch.setitem(sys.modules, "utils.responses", responses)

    module = importlib.import_module("opendss_tools.configuration")
    module.dss_tools = fake_tools
    module.state = state
    return module, fake_tools, state


def test_compile_rejects_explicit_unready_state(configuration_module, tmp_path):
    module, tools, state = configuration_module
    tools.configuration.circuit_readiness = lambda: {"ready": False}

    result = module.compile_opendss_file(str(tmp_path / "master.dss"))

    assert result["success"] is False
    assert "ready=false" in result["error"]
    assert state.circuit_loaded is False
    assert state.last_compiled_dss_file is None


def test_compile_rejects_empty_model_when_summary_exposes_bus_count(configuration_module, tmp_path):
    module, tools, state = configuration_module
    tools.model._summary_model_records = {"counts": {"buses": 0}}

    result = module.compile_opendss_file(str(tmp_path / "master.dss"))

    assert result["success"] is False
    assert "compiled no buses" in result["error"]
    assert state.circuit_loaded is False
    assert state.solution_available is False


def test_compile_accepts_nonempty_model(configuration_module, tmp_path):
    module, tools, state = configuration_module
    tools.configuration.circuit_readiness = lambda: {"ready": True}
    tools.model._summary_model_records = {"counts": {"buses": 13}}

    result = module.compile_opendss_file(str(tmp_path / "master.dss"))

    assert result["success"] is True
    assert result["payload"]["circuit_loaded"] is True
    assert state.circuit_loaded is True
    assert state.last_compiled_dss_file == str((tmp_path / "master.dss").resolve())


def test_rechecking_cached_compile_invalidates_stale_state(configuration_module, tmp_path):
    module, tools, state = configuration_module
    path = tmp_path / "master.dss"
    state.circuit_loaded = True
    state.last_compiled_dss_file = str(path.resolve())
    tools.model._summary_model_records = {"counts": {"buses": 0}}

    result = module.compile_opendss_file(str(path))

    assert result["success"] is False
    assert state.circuit_loaded is False
    assert state.last_compiled_dss_file is None
