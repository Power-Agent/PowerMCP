"""Engine-independent comparison of power-system time-domain trajectories.

Adapters must normalize channel names, units, and event-relative timestamps.
The comparison core uses only the Python standard library and never extrapolates.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Mapping


def _finite(value: Real, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number (bool is not allowed)")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _finite_result(value: float, name: str) -> float:
    """Reject arithmetic overflow instead of returning misleading infinities."""
    if not math.isfinite(value):
        raise ValueError(f"{name} overflowed or produced a non-finite result")
    return value


@dataclass(frozen=True)
class ChannelSeries:
    """One physical signal sampled at its own strictly increasing time points."""
    unit: str
    time_s: tuple[float, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("channel unit must be a non-empty string")
        try:
            times = tuple(_finite(v, "channel time_s") for v in self.time_s)
            values = tuple(_finite(v, "channel values") for v in self.values)
        except TypeError:
            raise
        except ValueError:
            raise
        if len(times) != len(values):
            raise ValueError("channel time_s and values must have equal lengths")
        if len(times) < 2:
            raise ValueError("each channel must contain at least two samples")
        if any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError("channel time_s must be strictly increasing")
        object.__setattr__(self, "time_s", times)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True)
class DynamicSnapshot:
    """Normalized output from one dynamic simulation.

    event_time_s is the physical event origin (e.g. fault application).
    disturbance_id identifies equivalent disturbance definitions.
    """
    engine: str
    case_id: str
    study_type: str
    disturbance_id: str
    event_time_s: float
    channels: Mapping[str, ChannelSeries]

    def __post_init__(self) -> None:
        for field in ("engine", "case_id", "study_type", "disturbance_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        _finite(self.event_time_s, "event_time_s")
        if not isinstance(self.channels, Mapping) or not self.channels:
            raise ValueError("channels must be a non-empty mapping")
        for key, series in self.channels.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("channel identifiers must be non-empty strings")
            if not isinstance(series, ChannelSeries):
                raise TypeError(f"channels[{key!r}] must be a ChannelSeries")


@dataclass(frozen=True)
class ChannelMetrics:
    channel: str
    unit: str
    samples_compared: int
    overlap_start_s: float
    overlap_end_s: float
    mean_absolute_error: float
    root_mean_square_error: float
    maximum_absolute_error: float
    integrated_absolute_error: float
    left_peak: float
    right_peak: float
    allowed_maximum_error: float
    within_tolerance: bool


@dataclass(frozen=True)
class DynamicComparisonReport:
    left_engine: str
    right_engine: str
    channels_compared: tuple[ChannelMetrics, ...]
    missing_from_left: tuple[str, ...]
    missing_from_right: tuple[str, ...]
    unit_mismatches: tuple[str, ...]
    insufficient_overlap: tuple[str, ...]
    outside_tolerance: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return bool(self.channels_compared) and not (
            self.missing_from_left or self.missing_from_right
            or self.unit_mismatches or self.insufficient_overlap
            or self.outside_tolerance
        )


def _interpolate(times: tuple[float, ...], values: tuple[float, ...], point: float) -> float:
    """Linear interpolation in-range only; extrapolation is forbidden."""
    if point < times[0] or point > times[-1]:
        raise ValueError("interpolation point lies outside the channel time range")
    lo, hi = 0, len(times) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if times[mid] < point:
            lo = mid
        else:
            hi = mid
    if point == times[lo]:
        return values[lo]
    if point == times[hi]:
        return values[hi]
    numerator = _finite_result(point - times[lo], "interpolation time difference")
    denominator = _finite_result(times[hi] - times[lo], "interpolation interval")
    fraction = _finite_result(numerator / denominator, "interpolation fraction")
    delta = _finite_result(values[hi] - values[lo], "interpolation value difference")
    return _finite_result(values[lo] + fraction * delta, "interpolated value")


def compare_dynamic_snapshots(
    left: DynamicSnapshot,
    right: DynamicSnapshot,
    *,
    max_points_per_channel: int = 100_000,
    minimum_overlap_s: float = 0.0,
    absolute_tolerance: float = 1e-6,
    relative_tolerance: float = 1e-5,
    channel_tolerances: Mapping[str, tuple[float, float]] | None = None,
) -> DynamicComparisonReport:
    """Compare trajectories on a common event-relative grid.

    The grid is the union of both sample grids inside their common interval.
    Linear interpolation is used only within observed ranges. MAE, RMSE and
    integrated absolute error use trapezoidal time integration. A channel passes
    when its maximum pointwise error is <= atol + rtol * peak signal magnitude.
    No unit conversion, extrapolation, or missing-channel suppression occurs.
    """
    if not isinstance(left, DynamicSnapshot) or not isinstance(right, DynamicSnapshot):
        raise TypeError("left and right must be DynamicSnapshot instances")
    if (left.case_id, left.study_type, left.disturbance_id) != (
        right.case_id, right.study_type, right.disturbance_id
    ):
        raise ValueError("cannot compare different case, study_type, or disturbance_id")
    if isinstance(max_points_per_channel, bool) or not isinstance(max_points_per_channel, int) or max_points_per_channel < 2:
        raise ValueError("max_points_per_channel must be an integer >= 2")
    minimum_overlap_s = _finite(minimum_overlap_s, "minimum_overlap_s")
    absolute_tolerance = _finite(absolute_tolerance, "absolute_tolerance")
    relative_tolerance = _finite(relative_tolerance, "relative_tolerance")
    if minimum_overlap_s < 0 or absolute_tolerance < 0 or relative_tolerance < 0:
        raise ValueError("overlap and comparison tolerances must be non-negative")
    if channel_tolerances is not None:
        if not isinstance(channel_tolerances, Mapping):
            raise TypeError("channel_tolerances must map IDs to (atol, rtol) pairs")
        for key, pair in channel_tolerances.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError("channel tolerances require non-empty IDs and (atol, rtol) pairs")
            atol, rtol = (_finite(pair[0], "channel atol"), _finite(pair[1], "channel rtol"))
            if atol < 0 or rtol < 0:
                raise ValueError("channel tolerances must be non-negative")

    lk, rk = set(left.channels), set(right.channels)
    common = lk & rk
    unused = set(channel_tolerances or {}) - common
    if unused:
        raise ValueError(f"unused channel tolerance keys: {sorted(unused)}")
    metrics, units, insufficient, outside = [], [], [], []
    for key in sorted(common):
        a, b = left.channels[key], right.channels[key]
        if a.unit != b.unit:
            units.append(key)
            continue
        at = tuple(
            _finite_result(t - left.event_time_s, "left event-relative timestamp")
            for t in a.time_s
        )
        bt = tuple(
            _finite_result(t - right.event_time_s, "right event-relative timestamp")
            for t in b.time_s
        )
        start, end = max(at[0], bt[0]), min(at[-1], bt[-1])
        duration = _finite_result(end - start, "overlap duration")
        if duration <= 0 or duration < minimum_overlap_s:
            insufficient.append(key)
            continue
        grid = sorted({start, end, *(t for t in at if start < t < end), *(t for t in bt if start < t < end)})
        if len(grid) > max_points_per_channel:
            raise ValueError(f"channel {key!r} alignment requires {len(grid)} points; limit is {max_points_per_channel}")
        av = tuple(_interpolate(at, a.values, t) for t in grid)
        bv = tuple(_interpolate(bt, b.values, t) for t in grid)
        errors = tuple(
            _finite_result(abs(x - y), f"absolute error for channel {key!r}")
            for x, y in zip(av, bv)
        )
        max_error = max(errors)

        # Normalize before squaring so large, but representable, errors do not
        # overflow merely because the RMSE calculation squares them.
        if max_error == 0:
            normalized_iae = 0.0
            normalized_ise = 0.0
        else:
            normalized = tuple(error / max_error for error in errors)
            normalized_iae = sum(
                (normalized[i] + normalized[i + 1]) * 0.5
                * (grid[i + 1] - grid[i])
                for i in range(len(grid) - 1)
            )
            normalized_ise = sum(
                (normalized[i] ** 2 + normalized[i + 1] ** 2) * 0.5
                * (grid[i + 1] - grid[i])
                for i in range(len(grid) - 1)
            )
        iae = _finite_result(max_error * normalized_iae, "integrated absolute error")
        mean_error = _finite_result(iae / duration, "mean absolute error")
        rms_error = _finite_result(
            max_error * math.sqrt(normalized_ise / duration),
            "root mean square error",
        )
        atol, rtol = (channel_tolerances or {}).get(key, (absolute_tolerance, relative_tolerance))
        signal_scale = max(max(map(abs, av)), max(map(abs, bv)))
        allowed = _finite_result(
            atol + _finite_result(rtol * signal_scale, "relative tolerance"),
            "combined tolerance",
        )
        within = max_error <= allowed
        if not within:
            outside.append(key)
        metrics.append(ChannelMetrics(
            channel=key, unit=a.unit, samples_compared=len(grid),
            overlap_start_s=start, overlap_end_s=end,
            mean_absolute_error=mean_error,
            root_mean_square_error=rms_error,
            maximum_absolute_error=max_error, integrated_absolute_error=iae,
            left_peak=max(av, key=abs), right_peak=max(bv, key=abs),
            allowed_maximum_error=allowed, within_tolerance=within,
        ))
    return DynamicComparisonReport(
        left_engine=left.engine, right_engine=right.engine,
        channels_compared=tuple(metrics),
        missing_from_left=tuple(sorted(rk - lk)),
        missing_from_right=tuple(sorted(lk - rk)),
        unit_mismatches=tuple(units),
        insufficient_overlap=tuple(insufficient),
        outside_tolerance=tuple(outside),
    )
