"""PowerFactory output labels and generated directories stay contained."""

from __future__ import annotations

import builtins
import importlib
import json
from types import SimpleNamespace

from PowerFactory.Agent_DIgSILENT import _ensure_output_directory, _safe_path_label


def test_powerfactory_output_label_cannot_be_a_parent_segment():
    assert _safe_path_label("..") == "run"
    nested = _safe_path_label("../../outside")
    assert ".." not in nested
    assert "/" not in nested


def test_powerfactory_generated_directory_checks_each_component(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    generated = allowed / "nested" / "results"
    assert _ensure_output_directory(str(generated), "output") == str(generated)
    assert generated.is_dir()


def test_powerfactory_server_creates_nested_configured_output(tmp_path, monkeypatch):
    original_print = builtins.print
    try:
        server = importlib.import_module("PowerFactory.MCP_PowerFactory")
    finally:
        builtins.print = original_print

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    config = allowed / "config.json"
    config.write_text("{}")
    generated = allowed / "nested" / "results"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    class Config:
        @classmethod
        def from_json(cls, path):
            assert path == str(config)
            return SimpleNamespace(output_dir=str(generated))

    class Agent:
        def __init__(self, cfg):
            self.cfg = cfg

        def run_pipeline(self):
            return {"success": True, "output_dir": self.cfg.output_dir}

    monkeypatch.setattr(server, "_load_modules", lambda: (Config, Agent))
    monkeypatch.setattr(server, "_pf", lambda function, *args: function(*args))

    result = json.loads(server.run_simulation(cfg_path=str(config)))

    assert result["success"] is True
    assert result["output_dir"] == str(generated)
    assert generated.is_dir()
