"""Normalized, engine-agnostic comparison of power-flow results.

Engine adapters should convert native solver outputs into a :class:`ResultSnapshot`
before comparison. The comparator deliberately does not run solvers or infer unit
conversions: adapters must provide normalized values and matching stable element IDs.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class ResultSnapshot:
    """A normalized result set for one solved network case.

    `values` keys should identify both the element and quantity, for example
    `bus:BUS-1:vm_pu` or `branch:LINE-1:p_from_mw`. Values must use the same
    units and sign conventions across engines.
    """

    engine: str
    case_id: str
    study_type: str
    base_mva: float
    converged: bool
    values: Mapping[str, float]


@dataclass(frozen=True)
class MetricTolerance:
    """Absolute-plus-relative tolerance for a normalized metric."""

    atol: float = 1e-6
    rtol: float = 1e-5

    def __post_init__(self) -> None:
        for name, value in (("atol", self.atol), ("rtol", self.rtol)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite non-negative number")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite non-negative number")


@dataclass(frozen=True)
class MetricDifference:
    metric: str
    left_value: float
    right_value: float
    absolute_error: float
    allowed_error: float


@dataclass(frozen=True)
class ComparisonReport:
    left_engine: str
    right_engine: str
    compared: int
    differences: tuple[MetricDifference, ...]
    missing_from_left: tuple[str, ...]
    missing_from_right: tuple[str, ...]
    convergence_mismatch: bool

    @property
    def passed(self) -> bool:
        return not (
            self.differences
            or self.missing_from_left
            or self.missing_from_right
            or self.convergence_mismatch
        )


def _validate_snapshot(snapshot: ResultSnapshot, side: str) -> None:
    for name in ("engine", "case_id", "study_type"):
        value = getattr(snapshot, name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{side}.{name} must be a non-empty string")
    if isinstance(snapshot.base_mva, bool) or not isinstance(snapshot.base_mva, (int, float)):
        raise TypeError(f"{side}.base_mva must be a finite positive number")
    if not math.isfinite(snapshot.base_mva) or snapshot.base_mva <= 0:
        raise ValueError(f"{side}.base_mva must be a finite positive number")
    if not isinstance(snapshot.converged, bool):
        raise TypeError(f"{side}.converged must be a bool")
    if not isinstance(snapshot.values, Mapping):
        raise TypeError(f"{side}.values must be a mapping")
    for key, value in snapshot.values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{side}.values contains an empty or non-string metric key")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{side}.values[{key!r}] must be numeric, not bool")
        if not math.isfinite(value):
            raise ValueError(f"{side}.values[{key!r}] must be finite")


def compare_snapshots(
    left: ResultSnapshot,
    right: ResultSnapshot,
    *,
    default_tolerance: MetricTolerance = MetricTolerance(),
    tolerances: Mapping[str, MetricTolerance] | None = None,
) -> ComparisonReport:
    """Compare two normalized results for the same case and study definition.

    Per-metric tolerances use exact metric keys. For each common metric, a match
    requires `abs(a-b) <= atol + rtol * max(abs(a), abs(b))`. Missing metrics
    are reported separately and never silently ignored.
    """
    _validate_snapshot(left, "left")
    _validate_snapshot(right, "right")
    if left.engine == right.engine:
        raise ValueError("snapshots must come from different engines")
    if left.case_id != right.case_id:
        raise ValueError("cannot compare different case_id values")
    if left.study_type != right.study_type:
        raise ValueError("cannot compare different study_type values")
    if not math.isclose(left.base_mva, right.base_mva, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("cannot compare snapshots with different base_mva values")
    if not isinstance(default_tolerance, MetricTolerance):
        raise TypeError("default_tolerance must be a MetricTolerance")
    if tolerances is not None:
        if not isinstance(tolerances, Mapping):
            raise TypeError("tolerances must be a mapping of metric keys to MetricTolerance")
        for key, tolerance in tolerances.items():
            if not isinstance(key, str) or not key:
                raise ValueError("tolerance metric keys must be non-empty strings")
            if not isinstance(tolerance, MetricTolerance):
                raise TypeError(f"tolerances[{key!r}] must be a MetricTolerance")

    left_keys, right_keys = set(left.values), set(right.values)
    common = sorted(left_keys & right_keys)
    differences: list[MetricDifference] = []
    for metric in common:
        a, b = float(left.values[metric]), float(right.values[metric])
        tolerance = (tolerances or {}).get(metric, default_tolerance)
        absolute_error = abs(a - b)
        allowed_error = tolerance.atol + tolerance.rtol * max(abs(a), abs(b))
        if absolute_error > allowed_error:
            differences.append(
                MetricDifference(metric, a, b, absolute_error, allowed_error)
            )

    return ComparisonReport(
        left_engine=left.engine,
        right_engine=right.engine,
        compared=len(common),
        differences=tuple(differences),
        missing_from_left=tuple(sorted(right_keys - left_keys)),
        missing_from_right=tuple(sorted(left_keys - right_keys)),
        convergence_mismatch=left.converged != right.converged,
    )
