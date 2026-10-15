"""Regression tests for duplicate/empty GenX capacity-cost selections."""

from __future__ import annotations

import pandas as pd
import pytest

from GenX.tool_logic import compute_capacity_cost as cost_module


def _write_case(tmp_path):
    case = tmp_path / "case"
    demand_dir = case / "inputs" / "inputs_p1" / "TDR_results"
    policy_dir = case / "inputs" / "inputs_p1" / "policies"
    result_dir = case / "results" / "results_p1"
    demand_dir.mkdir(parents=True)
    policy_dir.mkdir(parents=True)
    result_dir.mkdir(parents=True)

    pd.DataFrame(
        {
            "Timesteps_per_Rep_Period": [1, 1],
            "Sub_Weights": [1.0, 1.0],
            "Demand_MW_z1": [100.0, 120.0],
            "Demand_MW_z2": [200.0, 180.0],
        }
    ).to_csv(demand_dir / "Demand_data.csv", index=False)
    pd.DataFrame({"CapRes_1": [10.0, 20.0]}).to_csv(
        result_dir / "ReserveMargin_w.csv", index=False
    )
    pd.DataFrame(
        {
            "Network_zones": [1, 2],
            "CapRes_1": [0.1, 0.2],
        }
    ).to_csv(policy_dir / "Capacity_reserve_margin.csv", index=False)
    return case


@pytest.fixture
def case_path(tmp_path, monkeypatch):
    case = _write_case(tmp_path)
    monkeypatch.setattr(cost_module, "resolve_scenario", lambda *args, **kwargs: str(case))
    return str(case)


def test_duplicate_capres_regions_are_rejected(case_path):
    result = cost_module.compute_capacity_cost(case_path, capres_regions=[1, 1])

    assert result["success"] is False
    assert "Duplicate CapRes region(s): [1]" in result["message"]


def test_empty_capres_regions_are_rejected(case_path):
    result = cost_module.compute_capacity_cost(case_path, capres_regions=[])

    assert result["success"] is False
    assert "at least one region" in result["message"]


def test_duplicate_zones_are_rejected(case_path):
    result = cost_module.compute_capacity_cost(case_path, zones=[1, 1])

    assert result["success"] is False
    assert "Duplicate zone(s): [1]" in result["message"]


def test_empty_zones_are_rejected(case_path):
    result = cost_module.compute_capacity_cost(case_path, zones=[])

    assert result["success"] is False
    assert "at least one zone" in result["message"]


def test_unique_selections_still_compute_cost(case_path):
    result = cost_module.compute_capacity_cost(
        case_path, capres_regions=[1], zones=[1, 2]
    )

    assert result["success"] is True
    assert result["capres_regions"] == [1]
    assert result["zones"] == [1, 2]
    assert result["price_per_mw_day"] > 0
    assert result["price_per_mw_yr"] > 0
