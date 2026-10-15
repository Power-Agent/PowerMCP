"""Regression tests for PSS/E transient-response analysis."""

import math

import pytest

from PSSE.dynamic_stability import analyze_channel_series
from PSSE import psse_mcp


def test_reports_extrema_and_settling_time_with_irregular_timestamps():
    metrics = analyze_channel_series(
        [0.0, 0.1, 0.2, 0.4, 0.6, 1.0],
        {"1": [1.0, 1.4, 0.5, 1.02, 1.01, 1.0]},
        tolerance=0.03,
        settling_window=0.5,
    )["1"]

    assert metrics["minimum"] == 0.5
    assert metrics["minimum_time"] == 0.2
    assert metrics["maximum"] == 1.4
    assert metrics["maximum_time"] == 0.1
    assert metrics["peak_to_peak"] == pytest.approx(0.9)
    assert metrics["max_abs_deviation_from_final"] == pytest.approx(0.5)
    assert metrics["settled"] is True
    assert metrics["settling_time"] == 0.4


def test_late_excursion_prevents_false_settled_result():
    metrics = analyze_channel_series(
        [0, 1, 2, 3, 4],
        {1: [1.0, 1.01, 1.0, 1.4, 1.0]},
        tolerance=0.02,
        settling_window=1.0,
    )["1"]

    assert metrics["settled"] is False
    assert metrics["settling_time"] is None


def test_per_channel_tolerance_overrides_default():
    metrics = analyze_channel_series(
        [0, 1, 2, 3],
        {1: [1.0, 1.1, 1.02, 1.0], 2: [60.0, 60.1, 60.02, 60.0]},
        tolerance=0.01,
        settling_window=1.0,
        channel_tolerances={"1": 0.11, "2": 0.03},
    )

    assert metrics["1"]["tolerance"] == 0.11
    assert metrics["1"]["settled"] is True
    assert metrics["2"]["tolerance"] == 0.03
    assert metrics["2"]["settled"] is True


@pytest.mark.parametrize(
    ("time", "channels", "message"),
    [
        ([0, 1, 1], {1: [1, 2, 3]}, "strictly increasing"),
        ([0, math.inf], {1: [1, 2]}, "finite numeric"),
        ([0, 1], {1: [1]}, "expected 2 to match time"),
        ([0, 1], {1: [1, math.nan]}, "finite numeric"),
        ([0], {1: [1]}, "at least two samples"),
        ([0, 1], {}, "at least one dynamic channel"),
    ],
)
def test_rejects_invalid_dynamic_series(time, channels, message):
    with pytest.raises(ValueError, match=message):
        analyze_channel_series(time, channels)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"tolerance": -1}, "tolerance must be non-negative"),
        ({"settling_window": math.inf}, "settling_window must contain only finite"),
        ({"channel_tolerances": {"99": 0.1}}, "unknown channel"),
        ({"channel_tolerances": {"1": -0.1}}, "tolerance for channel '1' must be non-negative"),
    ],
)
def test_rejects_invalid_analysis_options(kwargs, message):
    with pytest.raises(ValueError, match=message):
        analyze_channel_series([0, 1], {"1": [1.0, 1.0]}, **kwargs)


def test_mcp_tool_returns_compact_metrics_without_raw_series(tmp_path, monkeypatch):
    outfile = tmp_path / "case.out"
    outfile.touch()

    class FakeCHNF:
        def __init__(self, path, outvrsn=0):
            self.path = path
            self.outvrsn = outvrsn

        def get_data(self):
            return (
                "test case",
                {"time": "Time(s)", 1: "Bus voltage"},
                {"time": [0.0, 0.5, 1.0, 1.5, 2.0], 1: [1.0, 0.8, 1.0, 1.0, 1.0]},
            )

    class FakeDyntools:
        CHNF = FakeCHNF

    monkeypatch.setattr(psse_mcp, "checked_path", lambda path, purpose: path)
    monkeypatch.setattr(psse_mcp, "_dyntools", lambda: FakeDyntools)

    result = psse_mcp.analyze_dynamic_stability(
        str(outfile), channels=[1], tolerance=0.01, settling_window=0.5
    )

    assert result["status"] == "success", result
    assert result["sample_count"] == 5
    assert result["channels"] == {"1": "Bus voltage"}
    assert result["metrics"]["1"]["minimum"] == 0.8
    assert result["metrics"]["1"]["minimum_time"] == 0.5
    assert result["metrics"]["1"]["settled"] is True
    assert "data" not in result


def test_mcp_tool_rejects_duplicate_channels_before_engine_start(tmp_path, monkeypatch):
    outfile = tmp_path / "case.out"
    outfile.touch()
    calls = []
    monkeypatch.setattr(psse_mcp, "checked_path", lambda path, purpose: path)
    monkeypatch.setattr(psse_mcp, "_dyntools", lambda: calls.append("engine"))

    result = psse_mcp.analyze_dynamic_stability(str(outfile), channels=[1, 1])

    assert result["status"] == "error"
    assert "duplicates" in result["message"]
    assert calls == []
