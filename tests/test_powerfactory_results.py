"""PowerFactory tools report through the shared result shape.

The tools return JSON strings rather than dicts, so the shape has to survive
serialization. PowerFactory itself is Windows-only vendor software; these tests
substitute the agent module, which is where every result originates.
"""

from __future__ import annotations

import builtins
import importlib
import json

import pytest


@pytest.fixture()
def server():
    """The server module, with print() restored after import.

    The module redirects print() to stderr at import so that no tool output
    reaches stdout, which is the JSON-RPC channel.
    """
    original_print = builtins.print
    try:
        return importlib.import_module("PowerFactory.MCP_PowerFactory")
    finally:
        builtins.print = original_print


def test_an_agent_failure_becomes_the_error_shape(server, monkeypatch):
    class Agent:
        @staticmethod
        def short_circuit(open_digsilent):
            return False, "No study case is active"

    monkeypatch.setattr(server, "_load_modules", lambda: (None, Agent))
    monkeypatch.setattr(server, "_pf", lambda function, *args: function(*args))

    result = json.loads(server.run_short_circuit())
    assert result == {"status": "error", "message": "No study case is active"}


def test_an_agent_success_becomes_the_success_shape(server, monkeypatch):
    class Agent:
        @staticmethod
        def short_circuit(open_digsilent):
            return True, "Short-circuit calculation OK"

    monkeypatch.setattr(server, "_load_modules", lambda: (None, Agent))
    monkeypatch.setattr(server, "_pf", lambda function, *args: function(*args))

    result = json.loads(server.run_short_circuit())
    assert result == {"status": "success", "message": "Short-circuit calculation OK"}


def test_a_refused_deletion_keeps_its_own_key_on_the_error_branch(server, monkeypatch):
    """`deleted` is documented on both branches, so it is present on both."""

    class Agent:
        @staticmethod
        def delete_component(*args):
            return False, "Component not found: Bus 99"

    monkeypatch.setattr(server, "_load_modules", lambda: (None, Agent))
    monkeypatch.setattr(server, "_pf", lambda function, *args: function(*args))

    result = json.loads(server.delete_component("bus", "Bus 99", confirmation="yes"))
    assert result["status"] == "error"
    assert result["deleted"] is False
    assert "Bus 99" in result["message"]


def test_a_missing_required_argument_is_reported_not_raised(server):
    result = json.loads(server.import_project(file_path=""))
    assert result == {"status": "error", "message": "file_path is required"}


def test_an_unsupported_component_category_names_the_supported_ones(server):
    result = json.loads(server.list_components(component_type="flux capacitors"))
    assert result["status"] == "error"
    assert "flux capacitors" in result["message"]
    assert "buses" in result["supported_component_types"]


def test_a_stopped_pipeline_carries_the_step_that_stopped_it(server, monkeypatch, tmp_path):
    """run_pipeline's report is the tool result, so it carries the shape."""

    class Config:
        output_dir = str(tmp_path)
        export_pfd = 0
        open_digsilent = 0

        @classmethod
        def from_json(cls, path):
            return cls()

    class Agent:
        def __init__(self, cfg):
            self.cfg = cfg

        def run_pipeline(self):
            return {
                "connect": {"ok": False, "msg": "PowerFactory is not running"},
                "status": "error",
                "message": (
                    "Pipeline stopped at step 'connect': "
                    "PowerFactory is not running"
                ),
            }

    monkeypatch.setattr(server, "_load_modules", lambda: (Config, Agent))
    monkeypatch.setattr(server, "_pf", lambda function, *args: function(*args))

    config = tmp_path / "config.json"
    config.write_text("{}")

    result = json.loads(server.run_simulation(cfg_path=str(config)))
    assert result["status"] == "error"
    assert "connect" in result["message"]
    assert result["connect"]["ok"] is False
