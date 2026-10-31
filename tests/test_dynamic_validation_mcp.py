from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def andes_validation_server(monkeypatch):
    """Load the ANDES MCP module with only its optional engine dependency stubbed."""
    repo_root = Path(__file__).resolve().parents[1]
    fake_andes = types.ModuleType("andes")
    fake_andes.config_logger = lambda **kwargs: None
    monkeypatch.setitem(sys.modules, "andes", fake_andes)

    module_path = repo_root / "ANDES" / "andes_mcp.py"
    spec = importlib.util.spec_from_file_location(
        "_andes_mcp_dynamic_validation_test", module_path
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_compare_tool_returns_deterministic_report_without_running_engine(
    andes_validation_server,
):
    left = {
        "engine": "psse", "case_id": "kundur", "study_type": "fault_response",
        "disturbance_id": "bus5_fault", "event_time_s": 0.1,
        "engine_version": "PSS/E 36.2",
        "simulation_settings": {"step_size": 0.01},
        "channels": {"bus:5:voltage": {
            "unit": "pu", "time_s": [0.0, 0.1, 0.2], "values": [1.0, 0.8, 0.9]
        }},
    }
    right = {
        "engine": "andes", "case_id": "kundur", "study_type": "fault_response",
        "disturbance_id": "bus5_fault", "event_time_s": 0.1,
        "engine_version": "ANDES 2.0",
        "simulation_settings": {"step_size": 0.005},
        "channels": {"bus:5:voltage": {
            "unit": "pu", "time_s": [0.0, 0.05, 0.1, 0.15, 0.2],
            "values": [1.0, 0.9, 0.8, 0.85, 0.9]
        }},
    }
    result = andes_validation_server.compare_dynamic_trajectories(
        left, right, absolute_tolerance=0.0, relative_tolerance=0.0
    )
    assert result["status"] == "success", result
    assert result["passed"] is True
    assert result["artifact"]["run_metadata"]["left"]["engine_version"] == "PSS/E 36.2"
    assert result["artifact"]["run_metadata"]["right"]["simulation_settings"]["step_size"] == 0.005
    assert result["json_report"] == andes_validation_server.compare_dynamic_trajectories(
        left, right, absolute_tolerance=0.0, relative_tolerance=0.0
    )["json_report"]


def test_mcp_compare_tool_returns_structured_error_for_incompatible_studies(
    andes_validation_server,
):
    snapshot = {
        "engine": "psse", "case_id": "case-a", "study_type": "fault",
        "disturbance_id": "fault-a", "event_time_s": 0.0,
        "channels": {"v": {"unit": "pu", "time_s": [0, 1], "values": [1, 0.9]}},
    }
    other = dict(snapshot, engine="andes", case_id="case-b")
    result = andes_validation_server.compare_dynamic_trajectories(snapshot, other)
    assert result["status"] == "error"
    assert "different case" in result["message"]


def test_mcp_export_tool_extracts_selected_andes_history(
    andes_validation_server, monkeypatch,
):
    class TS:
        t = [0.0, 0.1, 0.2]
        x = [[1.0], [0.8], [0.9]]
    class DAE:
        ts = TS()
    class System:
        dae = DAE()

    monkeypatch.setitem(andes_validation_server.system_state, "current_system", System())
    result = andes_validation_server.export_dynamic_validation_snapshot(
        channel_map={"bus:5:voltage": {"source": "x", "index": 0, "unit": "pu"}},
        case_id="kundur", study_type="fault_response",
        disturbance_id="bus5_fault", event_time_s=0.1,
        engine_version="ANDES 2.0", simulation_settings={"step_size": 0.01},
    )
    assert result["status"] == "success", result
    snapshot = result["snapshot"]
    assert snapshot["engine"] == "andes"
    assert snapshot["engine_version"] == "ANDES 2.0"
    assert snapshot["channels"]["bus:5:voltage"]["values"] == [1.0, 0.8, 0.9]


def test_mcp_export_tool_requires_a_loaded_system(andes_validation_server):
    result = andes_validation_server.export_dynamic_validation_snapshot(
        channel_map={"v": {"source": "x", "index": 0, "unit": "pu"}},
        case_id="case", study_type="fault", disturbance_id="fault", event_time_s=0.0,
    )
    assert result == {"status": "error", "message": "No ANDES system is loaded"}
