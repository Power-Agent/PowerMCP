"""JSON transport helpers for normalized transient snapshots."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .dynamic_validation import ChannelSeries, DynamicSnapshot


def dynamic_snapshot_to_dict(snapshot: DynamicSnapshot) -> dict[str, Any]:
    if not isinstance(snapshot, DynamicSnapshot):
        raise TypeError("snapshot must be a DynamicSnapshot")
    return {
        "engine": snapshot.engine,
        "case_id": snapshot.case_id,
        "study_type": snapshot.study_type,
        "disturbance_id": snapshot.disturbance_id,
        "event_time_s": snapshot.event_time_s,
        "engine_version": snapshot.engine_version,
        "simulation_settings": dict(snapshot.simulation_settings or {}),
        "channels": {
            key: {
                "unit": series.unit,
                "time_s": list(series.time_s),
                "values": list(series.values),
            }
            for key, series in sorted(snapshot.channels.items())
        },
    }


def dynamic_snapshot_from_dict(payload: Mapping[str, Any]) -> DynamicSnapshot:
    if not isinstance(payload, Mapping):
        raise TypeError("snapshot payload must be a mapping")
    required = {"engine", "case_id", "study_type", "disturbance_id", "event_time_s", "channels"}
    missing = required - set(payload)
    if missing:
        raise ValueError(f"snapshot payload is missing fields: {sorted(missing)}")
    raw_channels = payload["channels"]
    if not isinstance(raw_channels, Mapping):
        raise TypeError("snapshot channels must be a mapping")
    channels = {}
    for key, spec in raw_channels.items():
        if not isinstance(spec, Mapping) or "unit" not in spec or "time_s" not in spec or "values" not in spec:
            raise ValueError(f"snapshot channel {key!r} requires unit, time_s, and values")
        channels[key] = ChannelSeries(
            unit=spec["unit"], time_s=tuple(spec["time_s"]), values=tuple(spec["values"])
        )
    return DynamicSnapshot(
        engine=payload["engine"],
        case_id=payload["case_id"],
        study_type=payload["study_type"],
        disturbance_id=payload["disturbance_id"],
        event_time_s=payload["event_time_s"],
        channels=channels,
        engine_version=payload.get("engine_version"),
        simulation_settings=payload.get("simulation_settings"),
    )
