from __future__ import annotations

import json

import pytest

from powermcp.dynamic_validation import (
    ChannelSeries, DynamicSnapshot, compare_dynamic_snapshots,
)
from powermcp.dynamic_validation_adapters import (
    snapshot_from_andes_system,
    snapshot_from_andes_trajectories,
    snapshot_from_psse_output,
)
from powermcp.dynamic_validation_serialization import (
    dynamic_snapshot_from_dict,
    dynamic_snapshot_to_dict,
)
from powermcp.dynamic_validation_reporting import (
    build_dynamic_validation_artifact,
    dynamic_validation_json,
    dynamic_validation_markdown,
)


META = {
    "case_id": "kundur",
    "study_type": "fault_response",
    "disturbance_id": "bus5_3ph_fault",
    "event_time_s": 0.1,
}


def test_psse_adapter_normalizes_channel_ids_and_rejects_downsampled_data():
    payload = {
        "status": "success",
        "downsampled": False,
        "data": {"time": [0.0, 0.1, 0.2], "1": [1.0, 0.8, 0.9]},
    }
    snapshot = snapshot_from_psse_output(
        payload, channel_map={"bus:5:voltage": {"source": 1, "unit": "pu"}},
        **META,
    )
    assert snapshot.engine == "psse"
    assert snapshot.channels["bus:5:voltage"] == ChannelSeries(
        unit="pu", time_s=(0.0, 0.1, 0.2), values=(1.0, 0.8, 0.9)
    )
    payload["downsampled"] = True
    with pytest.raises(ValueError, match="downsampled"):
        snapshot_from_psse_output(
            payload, channel_map={"bus:5:voltage": {"source": 1, "unit": "pu"}},
            **META,
        )


def test_psse_adapter_rejects_missing_channels_and_unsuccessful_run():
    with pytest.raises(ValueError, match="not successful"):
        snapshot_from_psse_output({"status": "error"}, channel_map={"v": {"source": 1, "unit": "pu"}}, **META)
    with pytest.raises(ValueError, match="missing source"):
        snapshot_from_psse_output(
            {"status": "success", "data": {"time": [0, 1]}},
            channel_map={"v": {"source": 1, "unit": "pu"}}, **META,
        )


def test_andes_payload_adapter_requires_explicit_units_and_matching_lengths():
    snapshot = snapshot_from_andes_trajectories(
        [0.0, 0.1, 0.2],
        {"bus:5:voltage": {"values": [1.0, 0.8, 0.9], "unit": "pu"}},
        **META,
    )
    assert snapshot.engine == "andes"
    assert snapshot.channels["bus:5:voltage"].values == (1.0, 0.8, 0.9)
    with pytest.raises(ValueError, match="explicit unit"):
        snapshot_from_andes_trajectories(
            [0, 1], {"v": {"values": [1, 2]}}, **META
        )


class _FakeTS:
    t = [0.0, 0.1, 0.2]
    x = [[1.0, 2.0], [0.8, 2.1], [0.9, 2.2]]
    y = [[50.0], [49.9], [49.8]]


class _FakeSystem:
    class _DAE:
        ts = _FakeTS()
    dae = _DAE()


def test_andes_system_adapter_extracts_explicit_state_and_output_indices():
    snapshot = snapshot_from_andes_system(
        _FakeSystem(),
        channel_map={
            "bus:5:voltage": {"source": "x", "index": 0, "unit": "pu"},
            "machine:1:speed": {"source": "x", "index": 1, "unit": "pu"},
            "bus:5:frequency": {"source": "y", "index": 0, "unit": "Hz"},
        },
        **META,
    )
    assert snapshot.channels["bus:5:voltage"].values == (1.0, 0.8, 0.9)
    assert snapshot.channels["bus:5:frequency"].values == (50.0, 49.9, 49.8)


def test_andes_system_adapter_rejects_ambiguous_or_missing_history():
    class BadSystem:
        class DAE:
            class TS:
                t = [0.0, 1.0]
                x = [[1.0, 2.0, 3.0], [3.0, 4.0, 5.0]]
            ts = TS()
        dae = DAE()

    with pytest.raises(ValueError, match="selector"):
        snapshot_from_andes_system(
            BadSystem(),
            channel_map={"v": {"source": "x", "index": 4, "unit": "pu"}},
            **META,
        )
    with pytest.raises(ValueError, match="no time-series"):
        snapshot_from_andes_system(
            object(), channel_map={"v": {"source": "x", "index": 0, "unit": "pu"}},
            **META,
        )


def test_report_artifacts_are_deterministic_and_include_provenance():
    left = snapshot_from_andes_trajectories(
        [0, 1, 2], {"bus:5:voltage": {"values": [1, .8, .9], "unit": "pu"}},
        engine_version="ANDES 2.0",
        simulation_settings={"step_size": 0.01, "t_end": 2.0},
        **META,
    )
    right = DynamicSnapshot(
        engine="psse", case_id="kundur", study_type="fault_response",
        disturbance_id="bus5_3ph_fault", event_time_s=0.1,
        channels={"bus:5:voltage": ChannelSeries("pu", (0, 1, 2), (1, .8, .9))},
        engine_version="PSS/E 36.2",
        simulation_settings={"step_size": 0.01, "t_end": 2.0},
    )
    report = compare_dynamic_snapshots(left, right)
    artifact = build_dynamic_validation_artifact(
        left, right, report, comparison_settings={"absolute_tolerance": 1e-6},
    )
    encoded = dynamic_validation_json(artifact)
    assert encoded == dynamic_validation_json(artifact)
    parsed = json.loads(encoded)
    assert parsed["study"]["disturbance_id"] == "bus5_3ph_fault"
    assert parsed["run_metadata"]["left"]["engine_version"] == "ANDES 2.0"
    assert parsed["run_metadata"]["right"]["simulation_settings"]["t_end"] == 2.0
    markdown = dynamic_validation_markdown(artifact)
    assert "Cross-engine transient validation" in markdown
    assert "**Result:** PASS" in markdown
    assert "bus:5:voltage" in markdown



def test_snapshot_json_transport_round_trips_provenance_and_samples():
    original = snapshot_from_andes_trajectories(
        [0.0, 0.1], {"bus:5:voltage": {"values": [1.0, 0.9], "unit": "pu"}},
        engine_version="ANDES 2.0",
        simulation_settings={"step_size": 0.01},
        **META,
    )
    restored = dynamic_snapshot_from_dict(dynamic_snapshot_to_dict(original))
    assert restored == original


def test_andes_system_adapter_rejects_ambiguous_square_history():
    class SquareSystem:
        class DAE:
            class TS:
                t = [0.0, 1.0]
                x = [[1.0, 2.0], [3.0, 4.0]]
            ts = TS()
        dae = DAE()

    with pytest.raises(ValueError, match="ambiguous square shape"):
        snapshot_from_andes_system(
            SquareSystem(),
            channel_map={"v": {"source": "x", "index": 0, "unit": "pu"}},
            **META,
        )



def test_andes_snapshot_export_refuses_oversized_full_resolution_history():
    with pytest.raises(ValueError, match="max_points"):
        snapshot_from_andes_system(
            _FakeSystem(),
            channel_map={"v": {"source": "x", "index": 0, "unit": "pu"}},
            max_points=2,
            **META,
        )
    with pytest.raises(ValueError, match="max_cells"):
        snapshot_from_andes_system(
            _FakeSystem(),
            channel_map={
                "v": {"source": "x", "index": 0, "unit": "pu"},
                "w": {"source": "x", "index": 1, "unit": "pu"},
            },
            max_cells=5,
            **META,
        )
