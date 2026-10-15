"""Pure-Python transient response metrics for PSS/E dynamic output data."""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Mapping


def _finite_real(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must contain only real numeric values")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must contain only finite numeric values")
    return result


def _nonnegative_finite(value: Any, name: str) -> float:
    result = _finite_real(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def analyze_channel_series(
    time: Any,
    channels: Mapping[Any, Any],
    *,
    tolerance: float = 0.02,
    settling_window: float = 0.5,
    channel_tolerances: Mapping[str, float] | None = None,
) -> dict[str, dict[str, Any]]:
    """Summarize transient channels without returning their full time series.

    tolerance and channel_tolerances are absolute tolerances in each channel's
    native units. A channel is considered settled at the earliest sample after
    its last excursion outside the final-value band, provided the remaining
    simulation duration is at least settling_window seconds. This is a
    descriptive signal metric, not a substitute for a study-specific
    stability criterion.
    """
    default_tolerance = _nonnegative_finite(tolerance, "tolerance")
    required_window = _nonnegative_finite(settling_window, "settling_window")

    try:
        point_count = len(time)
    except (TypeError, AttributeError) as exc:
        raise ValueError("time must be a non-empty sized sequence") from exc
    if point_count < 2:
        raise ValueError("time must contain at least two samples")

    times = [_finite_real(value, "time") for value in time]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("time values must be strictly increasing")

    if not channels:
        raise ValueError("at least one dynamic channel is required")

    overrides = dict(channel_tolerances or {})
    channel_ids = {str(key) for key in channels}
    unknown = sorted(set(overrides) - channel_ids)
    if unknown:
        raise ValueError(f"channel_tolerances contains unknown channel(s): {unknown}")

    metrics: dict[str, dict[str, Any]] = {}
    for key, raw_values in channels.items():
        channel_id = str(key)
        try:
            if len(raw_values) != point_count:
                raise ValueError(
                    f"channel {channel_id!r} has {len(raw_values)} samples; "
                    f"expected {point_count} to match time"
                )
            values = [
                _finite_real(value, f"channel {channel_id!r}")
                for value in raw_values
            ]
        except TypeError as exc:
            raise ValueError(
                f"channel {channel_id!r} must be a sized numeric sequence"
            ) from exc

        channel_tolerance = _nonnegative_finite(
            overrides.get(channel_id, default_tolerance),
            f"tolerance for channel {channel_id!r}",
        )
        min_index = min(range(point_count), key=values.__getitem__)
        max_index = max(range(point_count), key=values.__getitem__)
        final_value = values[-1]
        last_outside = max(
            (
                index
                for index, value in enumerate(values)
                if abs(value - final_value) > channel_tolerance
            ),
            default=-1,
        )
        candidate_index = last_outside + 1
        settled = (
            candidate_index < point_count
            and times[-1] - times[candidate_index] >= required_window
        )
        settling_time = times[candidate_index] if settled else None

        metrics[channel_id] = {
            "sample_count": point_count,
            "initial_value": values[0],
            "final_value": final_value,
            "minimum": values[min_index],
            "minimum_index": min_index,
            "minimum_time": times[min_index],
            "maximum": values[max_index],
            "maximum_index": max_index,
            "maximum_time": times[max_index],
            "peak_to_peak": values[max_index] - values[min_index],
            "max_abs_deviation_from_final": max(
                abs(value - final_value) for value in values
            ),
            "tolerance": channel_tolerance,
            "settled": settled,
            "settling_time": settling_time,
        }
    return metrics
