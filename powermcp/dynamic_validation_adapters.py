"""Strict adapters from PSS/E and ANDES trajectory payloads to snapshots.

The adapters never infer physical equivalence or convert units. Callers provide
stable canonical channel IDs, source channel selectors, units, and study
provenance explicitly. They reject sampled/downsampled PSS/E payloads because
decimation can erase transient extrema and distort error metrics.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .dynamic_validation import ChannelSeries, DynamicSnapshot


def _metadata(*, engine: str, case_id: str, study_type: str,
              disturbance_id: str, event_time_s: float,
              engine_version: str | None = None,
              simulation_settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "engine": engine,
        "case_id": case_id,
        "study_type": study_type,
        "disturbance_id": disturbance_id,
        "event_time_s": event_time_s,
        "engine_version": engine_version,
        "simulation_settings": simulation_settings,
    }


def _channel_map(channel_map: Mapping[str, Mapping[str, Any]]) -> None:
    if not isinstance(channel_map, Mapping) or not channel_map:
        raise ValueError("channel_map must be a non-empty mapping")
    for canonical_id, spec in channel_map.items():
        if not isinstance(canonical_id, str) or not canonical_id.strip():
            raise ValueError("canonical channel IDs must be non-empty strings")
        if not isinstance(spec, Mapping):
            raise TypeError(f"channel_map[{canonical_id!r}] must be a mapping")
        if not isinstance(spec.get("unit"), str) or not spec["unit"].strip():
            raise ValueError(f"channel_map[{canonical_id!r}] requires an explicit unit")


def snapshot_from_psse_output(
    result: Mapping[str, Any],
    *,
    channel_map: Mapping[str, Mapping[str, Any]],
    case_id: str,
    study_type: str,
    disturbance_id: str,
    event_time_s: float,
    engine_version: str | None = None,
    simulation_settings: Mapping[str, Any] | None = None,
) -> DynamicSnapshot:
    """Normalize the result from PSSE.read_dynamic_output.

    channel_map entries use {"source": channel_number, "unit": "pu"}.
    PSS/E channel numbers are converted to strings to match the MCP response.
    Downsampled responses are rejected by default: transient validation must
    use full-resolution output, not the bounded display-oriented MCP sample.
    """
    if not isinstance(result, Mapping) or result.get("status") != "success":
        raise ValueError(f"PSS/E dynamic output was not successful: {result!r}")
    if result.get("downsampled") is True:
        raise ValueError(
            "PSS/E output was downsampled; increase max_points/max_cells and "
            "re-read the full-resolution trajectory before validation"
        )
    data = result.get("data")
    if not isinstance(data, Mapping) or "time" not in data:
        raise ValueError("PSS/E result must contain data.time and channel arrays")
    _channel_map(channel_map)
    times = data["time"]
    if not isinstance(times, Sequence) or isinstance(times, (str, bytes)):
        raise TypeError("PSS/E data.time must be a sequence")
    channels: dict[str, ChannelSeries] = {}
    for canonical_id, spec in channel_map.items():
        source_value = spec.get("source")
        if isinstance(source_value, bool) or not isinstance(source_value, int) or source_value < 1:
            raise ValueError(
                f"channel_map[{canonical_id!r}] source must be a positive PSS/E channel number"
            )
        source = str(source_value)
        if source not in data:
            raise ValueError(f"PSS/E output is missing source channel {source!r}")
        channels[canonical_id] = ChannelSeries(
            unit=spec["unit"], time_s=tuple(times), values=tuple(data[source])
        )
    return DynamicSnapshot(
        **_metadata(engine="psse", case_id=case_id, study_type=study_type,
                    disturbance_id=disturbance_id, event_time_s=event_time_s,
                    engine_version=engine_version,
                    simulation_settings=simulation_settings),
        channels=channels,
    )


def snapshot_from_andes_trajectories(
    time_s: Sequence[float],
    trajectories: Mapping[str, Mapping[str, Any]],
    *,
    case_id: str,
    study_type: str,
    disturbance_id: str,
    event_time_s: float,
    engine_version: str | None = None,
    simulation_settings: Mapping[str, Any] | None = None,
) -> DynamicSnapshot:
    """Normalize explicitly selected ANDES trajectories.

    Each trajectory is keyed by a canonical physical channel ID and contains
    {"values": sequence, "unit": explicit-unit}. This intentionally avoids
    guessing whether an ANDES state is voltage, speed, angle, or another
    physical quantity from its internal variable name.
    """
    if not isinstance(trajectories, Mapping) or not trajectories:
        raise ValueError("trajectories must be a non-empty mapping")
    channels: dict[str, ChannelSeries] = {}
    for canonical_id, spec in trajectories.items():
        if not isinstance(canonical_id, str) or not canonical_id.strip():
            raise ValueError("canonical channel IDs must be non-empty strings")
        if not isinstance(spec, Mapping) or "values" not in spec or "unit" not in spec:
            raise ValueError(
                f"ANDES trajectory {canonical_id!r} requires values and explicit unit"
            )
        channels[canonical_id] = ChannelSeries(
            unit=spec["unit"], time_s=tuple(time_s), values=tuple(spec["values"])
        )
    return DynamicSnapshot(
        **_metadata(engine="andes", case_id=case_id, study_type=study_type,
                    disturbance_id=disturbance_id, event_time_s=event_time_s,
                    engine_version=engine_version,
                    simulation_settings=simulation_settings),
        channels=channels,
    )


def snapshot_from_andes_system(
    system: Any,
    *,
    channel_map: Mapping[str, Mapping[str, Any]],
    case_id: str,
    study_type: str,
    disturbance_id: str,
    event_time_s: float,
    engine_version: str | None = None,
    simulation_settings: Mapping[str, Any] | None = None,
    max_points: int = 100000,
    max_cells: int = 1000000,
) -> DynamicSnapshot:
    """Extract selected ANDES TDS state/output arrays using explicit selectors.

    Each channel map entry is {"source": "x"|"y", "index": integer,
    "unit": "..."}; x denotes differential states and y algebraic variables.
    The ANDES time-series matrix must be sample-major or signal-major with an
    unambiguous shape. Missing history or ambiguous dimensions are errors.
    """
    _channel_map(channel_map)
    for name, value in (("max_points", max_points), ("max_cells", max_cells)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError(f"{name} must be an integer >= 2")
    dae = getattr(system, "dae", None)
    ts = getattr(dae, "ts", None)
    if ts is None:
        raise ValueError("ANDES system has no time-series history (dae.ts)")
    times_obj = getattr(ts, "t", None)
    if times_obj is None:
        raise ValueError("ANDES time-series history has no time vector")
    times = tuple(times_obj.tolist() if hasattr(times_obj, "tolist") else times_obj)
    if len(times) < 2:
        raise ValueError("ANDES time-series history must contain at least two time points")
    if len(times) > max_points:
        raise ValueError(
            f"ANDES history has {len(times)} points; max_points={max_points}. "
            "Increase the cap and re-export; validation never downsamples."
        )
    required_cells = len(times) * (len(channel_map) + 1)  # include the shared time vector
    if required_cells > max_cells:
        raise ValueError(
            f"ANDES history requires {required_cells} channel cells; "
            f"max_cells={max_cells}. Increase the cap; validation never downsamples."
        )

    matrices: dict[str, list[list[Any]]] = {}
    for kind in ("x", "y"):
        raw = getattr(ts, kind, None)
        if raw is None:
            continue
        matrix = raw.tolist() if hasattr(raw, "tolist") else raw
        if not isinstance(matrix, Sequence) or not matrix:
            continue
        if not isinstance(matrix[0], Sequence):
            raise ValueError(f"ANDES dae.ts.{kind} must be a two-dimensional matrix")
        rows = [list(row) for row in matrix]
        if len(rows) == len(times) and len(rows[0]) == len(times):
            raise ValueError(
                f"ANDES dae.ts.{kind} has an ambiguous square shape; "
                "the adapter cannot infer its sample axis"
            )
        if len(rows) == len(times):
            matrices[kind] = rows
        elif len(rows[0]) == len(times):
            matrices[kind] = [list(column) for column in zip(*rows)]
        else:
            raise ValueError(
                f"ANDES dae.ts.{kind} shape does not match {len(times)} time points"
            )

    channels: dict[str, ChannelSeries] = {}
    for canonical_id, spec in channel_map.items():
        source = spec.get("source")
        index = spec.get("index")
        if not isinstance(source, str) or source not in {"x", "y"}:
            raise ValueError(f"ANDES channel {canonical_id!r} source must be 'x' or 'y'")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError(f"ANDES channel {canonical_id!r} index must be >= 0")
        if source not in matrices or index >= len(matrices[source][0]):
            raise ValueError(f"ANDES channel {canonical_id!r} selector is unavailable")
        channels[canonical_id] = ChannelSeries(
            unit=spec["unit"], time_s=times,
            values=tuple(row[index] for row in matrices[source]),
        )
    return DynamicSnapshot(
        **_metadata(engine="andes", case_id=case_id, study_type=study_type,
                    disturbance_id=disturbance_id, event_time_s=event_time_s,
                    engine_version=engine_version,
                    simulation_settings=simulation_settings),
        channels=channels,
    )
