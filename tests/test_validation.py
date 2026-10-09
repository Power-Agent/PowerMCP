"""Tests for normalized cross-engine result comparison."""
from __future__ import annotations

import pytest

from powermcp.validation import (
    MetricTolerance,
    ResultSnapshot,
    compare_snapshots,
)


def snapshot(engine="pandapower", values=None, **overrides):
    fields = {
        "engine": engine,
        "case_id": "ieee9",
        "study_type": "ac_power_flow",
        "base_mva": 100.0,
        "converged": True,
        "values": values
        if values is not None
        else {
            "bus:BUS-1:vm_pu": 1.02,
            "branch:LINE-1:p_from_mw": 12.5,
        },
    }
    fields.update(overrides)
    return ResultSnapshot(**fields)


def test_identical_normalized_results_pass():
    report = compare_snapshots(snapshot(), snapshot("pypsa"))

    assert report.passed
    assert report.compared == 2
    assert report.differences == ()
    assert report.missing_from_left == ()
    assert report.missing_from_right == ()


def test_empty_snapshots_do_not_pass_without_compared_metrics():
    report = compare_snapshots(snapshot(values={}), snapshot("andes", values={}))

    assert not report.passed
    assert report.compared == 0


def test_absolute_and_relative_tolerance_are_combined():
    left = snapshot(values={"bus:B1:vm_pu": 1.0})
    right = snapshot("andes", values={"bus:B1:vm_pu": 1.000009})

    assert compare_snapshots(
        left, right, default_tolerance=MetricTolerance(atol=1e-6, rtol=1e-5)
    ).passed


def test_metric_outside_tolerance_is_reported_deterministically():
    left = snapshot(values={"bus:B2:vm_pu": 0.98, "bus:B1:vm_pu": 1.0})
    right = snapshot(
        "egret", values={"bus:B1:vm_pu": 1.0, "bus:B2:vm_pu": 1.01}
    )

    report = compare_snapshots(
        left, right, default_tolerance=MetricTolerance(atol=1e-5, rtol=0.0)
    )

    assert not report.passed
    assert [difference.metric for difference in report.differences] == [
        "bus:B2:vm_pu"
    ]
    assert report.differences[0].absolute_error == pytest.approx(0.03)


def test_per_metric_tolerance_overrides_default():
    left = snapshot(values={"bus:B1:vm_pu": 1.0, "branch:L1:p_from_mw": 20.0})
    right = snapshot(
        "andes", values={"bus:B1:vm_pu": 1.0001, "branch:L1:p_from_mw": 20.01}
    )

    report = compare_snapshots(
        left,
        right,
        default_tolerance=MetricTolerance(atol=1e-6, rtol=0.0),
        tolerances={
            "bus:B1:vm_pu": MetricTolerance(atol=2e-4, rtol=0.0),
            "branch:L1:p_from_mw": MetricTolerance(atol=0.02, rtol=0.0),
        },
    )

    assert report.passed


def test_missing_metrics_are_not_silently_ignored():
    left = snapshot(values={"bus:B1:vm_pu": 1.0})
    right = snapshot("andes", values={"bus:B1:vm_pu": 1.0, "bus:B2:vm_pu": 0.99})

    report = compare_snapshots(left, right)

    assert not report.passed
    assert report.missing_from_left == ("bus:B2:vm_pu",)
    assert report.missing_from_right == ()


def test_convergence_mismatch_fails_even_if_values_match():
    report = compare_snapshots(
        snapshot(converged=True), snapshot("andes", converged=False)
    )

    assert not report.passed
    assert report.convergence_mismatch


@pytest.mark.parametrize(
    ("left_overrides", "right_overrides", "message"),
    [
        ({"case_id": "case-a"}, {"case_id": "case-b"}, "case_id"),
        ({"study_type": "ac"}, {"study_type": "dc"}, "study_type"),
        ({"base_mva": 100.0}, {"base_mva": 50.0}, "base_mva"),
    ],
)
def test_incompatible_studies_are_rejected(left_overrides, right_overrides, message):
    with pytest.raises(ValueError, match=message):
        compare_snapshots(snapshot(**left_overrides), snapshot("andes", **right_overrides))


def test_same_engine_is_rejected():
    with pytest.raises(ValueError, match="different engines"):
        compare_snapshots(snapshot(), snapshot("pandapower"))


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), True, "1.0"])
def test_invalid_metric_values_are_rejected(invalid):
    with pytest.raises((TypeError, ValueError)):
        compare_snapshots(
            snapshot(values={"bus:B1:vm_pu": invalid}),
            snapshot("andes", values={"bus:B1:vm_pu": 1.0}),
        )


@pytest.mark.parametrize("atol,rtol", [(-1, 0), (0, -1), (float("nan"), 0), (0, float("inf"))])
def test_invalid_tolerances_are_rejected(atol, rtol):
    with pytest.raises((TypeError, ValueError)):
        MetricTolerance(atol=atol, rtol=rtol)


def test_invalid_tolerance_mapping_is_rejected():
    with pytest.raises(TypeError, match="MetricTolerance"):
        compare_snapshots(
            snapshot(),
            snapshot("andes"),
            tolerances={"bus:BUS-1:vm_pu": 0.1},
        )
