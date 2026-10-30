from __future__ import annotations

import math

import pytest

from powermcp.dynamic_validation import (
    ChannelSeries, DynamicSnapshot, compare_dynamic_snapshots,
)


def series(times=(0, 1, 2), values=(0, 1, 0), unit="pu"):
    return ChannelSeries(unit=unit, time_s=times, values=values)


def snap(engine="psse", channels=None, event=0):
    return DynamicSnapshot(
        engine=engine, case_id="ieee9", study_type="fault_response",
        disturbance_id="bus5_3ph_0.1s", event_time_s=event,
        channels=channels if channels is not None else {"bus:5:voltage": series()},
    )


def test_identical_traces_pass_with_zero_error():
    report = compare_dynamic_snapshots(snap(), snap("andes"))
    assert report.passed
    metric = report.channels_compared[0]
    assert metric.mean_absolute_error == 0
    assert metric.root_mean_square_error == 0
    assert metric.maximum_absolute_error == 0
    assert metric.integrated_absolute_error == 0
    assert metric.samples_compared == 3


def test_different_solver_steps_align_on_union_grid():
    left = snap(channels={"v": series((0, 1, 2), (0, 1, 0))})
    right = snap("andes", {"v": series((0, .5, 1, 1.5, 2), (0, .5, 1, .5, 0))})
    report = compare_dynamic_snapshots(left, right)
    assert report.passed
    assert report.channels_compared[0].samples_compared == 5


def test_event_times_are_removed_before_alignment():
    left = snap(event=10, channels={"v": series((10, 11, 12), (0, 1, 0))})
    right = snap("andes", {"v": series((20, 21, 22), (0, 1, 0))}, event=20)
    assert compare_dynamic_snapshots(left, right).passed


def test_partial_overlap_is_compared_without_extrapolation():
    left = snap(channels={"v": series((0, 1, 2), (0, 1, 0))})
    right = snap("andes", {"v": series((1, 2, 3), (1, 0, 1))})
    metric = compare_dynamic_snapshots(left, right).channels_compared[0]
    assert (metric.overlap_start_s, metric.overlap_end_s) == (1, 2)
    assert metric.maximum_absolute_error == 0


def test_no_common_overlap_does_not_pass():
    left = snap(channels={"v": series((0, 1), (0, 1))})
    right = snap("andes", {"v": series((2, 3), (0, 1))})
    report = compare_dynamic_snapshots(left, right)
    assert not report.passed
    assert report.insufficient_overlap == ("v",)


def test_missing_channels_are_reported_on_both_sides():
    report = compare_dynamic_snapshots(
        snap(channels={"a": series()}), snap("andes", {"b": series()})
    )
    assert not report.passed
    assert report.missing_from_left == ("b",)
    assert report.missing_from_right == ("a",)


def test_unit_mismatch_is_never_silently_converted():
    report = compare_dynamic_snapshots(
        snap(channels={"v": series(unit="pu")}),
        snap("andes", {"v": series(unit="kV")}),
    )
    assert not report.passed
    assert report.unit_mismatches == ("v",)


def test_metrics_use_time_weighted_trapezoidal_integration():
    left = snap(channels={"x": series((0, 2), (0, 0), "MW")})
    right = snap("andes", {"x": series((0, 2), (2, 2), "MW")})
    metric = compare_dynamic_snapshots(left, right).channels_compared[0]
    assert metric.mean_absolute_error == pytest.approx(2)
    assert metric.root_mean_square_error == pytest.approx(2)
    assert metric.maximum_absolute_error == pytest.approx(2)
    assert metric.integrated_absolute_error == pytest.approx(4)


def test_oscillatory_disagreement_is_captured_by_peak_error():
    left = snap(channels={"f": series((0, 1, 2), (0, 1, 0), "Hz")})
    right = snap("andes", {"f": series((0, 1, 2), (0, -1, 0), "Hz")})
    metric = compare_dynamic_snapshots(left, right).channels_compared[0]
    assert metric.maximum_absolute_error == pytest.approx(2)
    assert metric.left_peak == 1
    assert metric.right_peak == -1


@pytest.mark.parametrize("times,values", [
    ((0, 1), (0,)), ((0, 0), (1, 2)), ((1, 0), (1, 2)),
    ((0, float("nan")), (1, 2)), ((0, 1), (1, float("inf"))),
    ((0,), (1,)), ((False, 1), (1, 2)),
])
def test_invalid_channel_series_are_rejected(times, values):
    with pytest.raises((TypeError, ValueError)):
        series(times, values)


@pytest.mark.parametrize("event", [float("nan"), float("inf"), True, "0"])
def test_invalid_event_time_is_rejected(event):
    with pytest.raises((TypeError, ValueError)):
        snap(event=event)


def test_incompatible_case_study_or_disturbance_is_rejected():
    left = snap()
    right = DynamicSnapshot("andes", "other", "fault_response", "bus5_3ph_0.1s", 0, {"x": series()})
    with pytest.raises(ValueError, match="case"):
        compare_dynamic_snapshots(left, right)


def test_alignment_point_budget_is_enforced():
    left = snap(channels={"x": series(tuple(range(5)), tuple(range(5)))})
    right = snap("andes", {"x": series(tuple(i / 2 for i in range(9)), tuple(i / 2 for i in range(9)))})
    with pytest.raises(ValueError, match="limit"):
        compare_dynamic_snapshots(left, right, max_points_per_channel=5)


def test_minimum_overlap_is_enforced():
    left = snap(channels={"x": series((0, 1, 2), (0, 1, 0))})
    right = snap("andes", {"x": series((1, 2, 3), (1, 0, 1))})
    report = compare_dynamic_snapshots(left, right, minimum_overlap_s=1.1)
    assert not report.passed
    assert report.insufficient_overlap == ("x",)


def test_invalid_point_budgets_and_negative_overlap_are_rejected():
    with pytest.raises(ValueError):
        compare_dynamic_snapshots(snap(), snap("andes"), max_points_per_channel=1)
    with pytest.raises(ValueError):
        compare_dynamic_snapshots(snap(), snap("andes"), minimum_overlap_s=-1)


def test_material_trajectory_difference_fails_default_tolerance():
    left = snap(channels={"v": series((0, 1, 2), (0, 1, 0))})
    right = snap("andes", {"v": series((0, 1, 2), (0, .8, 0))})
    report = compare_dynamic_snapshots(left, right)
    assert not report.passed
    assert report.outside_tolerance == ("v",)
    assert not report.channels_compared[0].within_tolerance


def test_channel_specific_tolerance_is_explicit_and_applied():
    left = snap(channels={"v": series((0, 1, 2), (0, 1, 0))})
    right = snap("andes", {"v": series((0, 1, 2), (0, .99, 0))})
    report = compare_dynamic_snapshots(
        left, right, absolute_tolerance=0, relative_tolerance=0,
        channel_tolerances={"v": (.02, 0)},
    )
    assert report.passed
    assert report.channels_compared[0].allowed_maximum_error == pytest.approx(.02)


@pytest.mark.parametrize("kwargs", [
    {"absolute_tolerance": -1}, {"relative_tolerance": float("nan")},
    {"channel_tolerances": {"v": (-1, 0)}},
    {"channel_tolerances": {"v": (0, float("inf"))}},
    {"channel_tolerances": {"v": (0,)}},
])
def test_invalid_tolerances_are_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        compare_dynamic_snapshots(snap(), snap("andes"), **kwargs)


def test_unknown_channel_tolerance_key_is_rejected():
    with pytest.raises(ValueError, match="unused"):
        compare_dynamic_snapshots(
            snap(), snap("andes"), channel_tolerances={"typo": (1, 0)}
        )


def test_report_order_is_deterministic():
    left = snap(channels={"z": series(), "a": series()})
    right = snap("andes", {"z": series(), "a": series()})
    report = compare_dynamic_snapshots(left, right)
    assert [item.channel for item in report.channels_compared] == ["a", "z"]



def test_constant_signal_uses_signal_magnitude_for_relative_tolerance():
    left = snap(channels={"v": series((0, 1, 2), (1e12, 1e12, 1e12), "V")})
    right = snap("andes", {"v": series((0, 1, 2), (1e12 + 1e6, 1e12 + 1e6, 1e12 + 1e6), "V")})
    report = compare_dynamic_snapshots(
        left, right, absolute_tolerance=0, relative_tolerance=2e-6,
    )
    metric = report.channels_compared[0]
    assert metric.allowed_maximum_error == pytest.approx(2e6)
    assert metric.mean_absolute_error == pytest.approx(1e6)
    assert metric.root_mean_square_error == pytest.approx(1e6)
    assert metric.within_tolerance


def test_large_finite_signal_error_does_not_overflow_during_rms():
    left = snap(channels={"x": series((0, 1), (0, 0), "MW")})
    right = snap("andes", {"x": series((0, 1), (1e200, 1e200), "MW")})
    metric = compare_dynamic_snapshots(
        left, right, absolute_tolerance=1e200, relative_tolerance=0,
    ).channels_compared[0]
    assert math.isfinite(metric.root_mean_square_error)
    assert metric.root_mean_square_error == pytest.approx(1e200)


def test_extreme_finite_values_that_overflow_subtraction_are_rejected():
    left = snap(channels={"x": series((0, 1), (-1e308, -1e308), "MW")})
    right = snap("andes", {"x": series((0, 1), (1e308, 1e308), "MW")})
    with pytest.raises(ValueError, match="absolute error"):
        compare_dynamic_snapshots(left, right)


def test_extreme_event_time_subtraction_is_rejected():
    left = snap(event=1e308, channels={"x": series((-1e308, -1e308 + 1e292), (0, 1))})
    right = snap("andes", {"x": series((0, 1), (0, 1))}, event=0)
    with pytest.raises(ValueError, match="event-relative timestamp"):
        compare_dynamic_snapshots(left, right)


def test_non_finite_intermediate_tolerance_is_rejected():
    left = snap(channels={"x": series((0, 1), (1e308, 1e308), "MW")})
    right = snap("andes", {"x": series((0, 1), (1e308, 1e308), "MW")})
    with pytest.raises(ValueError, match="relative tolerance"):
        compare_dynamic_snapshots(left, right, relative_tolerance=2.0)
