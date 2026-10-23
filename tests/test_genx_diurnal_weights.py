"""Regression tests for GenX representative-period time-weight validation."""

from __future__ import annotations

import pytest

from GenX.tool_logic.diurnal_generation import diurnal_by_tech


def _write_case(tmp_path, weights):
    case = tmp_path / "case"
    results = case / "results" / "results_p1"
    results.mkdir(parents=True)
    rows = [
        "Resource,MA_coal,MA_solar_pv",
        "Zone,1,1",
        "AnnualSum,0,0",
    ]
    rows.extend(f"t{i},{100 + i},{50 + i}" for i in range(len(weights)))
    (results / "power.csv").write_text("\n".join(rows) + "\n")
    weight_rows = ["Weight", *(str(weight) for weight in weights)]
    (results / "time_weights.csv").write_text("\n".join(weight_rows) + "\n")
    return case


def test_diurnal_rejects_nonfinite_time_weights(tmp_path):
    weights = [1.0] * 24
    weights[5] = float("nan")
    case = _write_case(tmp_path, weights)

    with pytest.raises(ValueError, match="time weights must all be finite"):
        diurnal_by_tech(str(case), period=1)


def test_diurnal_rejects_negative_time_weights(tmp_path):
    weights = [1.0] * 24
    weights[5] = -0.5
    case = _write_case(tmp_path, weights)

    with pytest.raises(ValueError, match="time weights must be non-negative"):
        diurnal_by_tech(str(case), period=1)


def test_diurnal_rejects_hour_with_zero_total_weight(tmp_path):
    # Two days ensure hour 3 has no weighted observations at all.
    weights = [1.0] * 48
    weights[3] = 0.0
    weights[27] = 0.0
    case = _write_case(tmp_path, weights)

    with pytest.raises(ValueError, match=r"hour\(s\) \[3\]"):
        diurnal_by_tech(str(case), period=1)


def test_diurnal_computes_profile_when_every_hour_has_weight(tmp_path):
    case = _write_case(tmp_path, [1.0] * 24)

    result = diurnal_by_tech(str(case), period=1)

    assert result.shape == (24, 2)
    assert result["Coal"].tolist() == [100 + hour for hour in range(24)]
    assert result["Solar"].tolist() == [50 + hour for hour in range(24)]



def test_diurnal_groups_use_shared_classification_and_display_labels(tmp_path):
    from GenX.tool_logic.diurnal_generation import diurnal_by_tech

    case = _write_case(
        tmp_path,
        [1.0] * 24,
    )
    result = diurnal_by_tech(str(case), period=1)

    assert "Coal" in result.columns
    assert "Solar" in result.columns
    assert result.shape == (24, 2)
