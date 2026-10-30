import json
import os
import sys

import pytest

pytest.importorskip("onsset")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import onsset_engine as eng  # noqa: E402
import onsset_params as op  # noqa: E402

REQUIRED = {"start_year": 2024, "end_year": 2050, "end_year_pop": 86e6, "urban_ratio_end_year": 0.36}


def test_required_params():
    assert op.REQUIRED_PARAMS == ("start_year", "end_year", "end_year_pop", "urban_ratio_end_year")


def test_defaults_fill_missing_values():
    p = eng.resolve_params(REQUIRED)
    assert p["diesel_price"] == op.DEFAULT_PARAMS["diesel_price"] == 1.43
    assert set(p) == set(op.ScenarioParams.model_fields)


def test_baseline_params_valid():
    with open(os.path.join(HERE, "baseline_uganda", "params.json")) as f:
        params = json.load(f)
    assert eng.resolve_params(params)["end_year_pop"] == 86000000


def test_unknown_parameter_rejected():
    with pytest.raises(ValueError, match="productive_demand"):
        eng.resolve_params({**REQUIRED, "productive_demand": 1})


def test_missing_required_parameter_rejected():
    with pytest.raises(ValueError, match="end_year_pop"):
        eng.resolve_params({k: v for k, v in REQUIRED.items() if k != "end_year_pop"})


@pytest.mark.parametrize("override, message", [
    ({"end_year": 2020}, "end_year must be after start_year"),
    ({"urban_ratio_end_year": 1.5}, "urban_ratio_end_year"),
    ({"grid_losses": 1}, "grid_losses"),
    ({"prio_choice": 6}, "prio_choice"),
    ({"urban_target_tier": 7}, "urban_target_tier"),
    ({"grid_reliability_option": "cnse"}, "grid_reliability_option"),
    ({"tier_3": 50}, "strictly increasing"),
    ({"intermediate_targets": {2055: 0.9}}, "strictly between"),
    ({"intermediate_targets": {2030: 0.9, 2040: 0.8}}, "must not decrease"),
    ({"intermediate_targets": {2030: 0.9}, "end_electrification_rate_target": 0.8}, "below the intermediate"),
])
def test_invalid_values_rejected(override, message):
    with pytest.raises(ValueError, match=message):
        eng.resolve_params({**REQUIRED, **override})


def test_single_step_horizon():
    years, limits, steps = eng.time_horizon(eng.resolve_params(REQUIRED))
    assert years == [2050]
    assert limits == {2050: 1.0}
    assert steps == {2050: 26}


def test_intermediate_targets_from_json_strings():
    p = eng.resolve_params({**REQUIRED, "intermediate_targets": {"2030": 0.8}})
    years, limits, steps = eng.time_horizon(p)
    assert years == [2030, 2050]
    assert limits == {2030: 0.8, 2050: 1.0}
    assert steps == {2030: 6, 2050: 20}


def test_build_tech_info_uses_explicit_costs():
    tech = eng.build_tech_info(eng.resolve_params({**REQUIRED, "pv_cost": 999, "wind_cost": 1234}))
    assert tech["mg_pv_hybrid_params"]["pv_cost"] == 999
    assert tech["mg_wind_hybrid_params"]["wind_cost"] == 1234


def test_describe_parameters_covers_every_field():
    groups = op.describe_parameters()
    described = [p for params in groups.values() for p in params]
    assert {p["name"] for p in described} == set(op.ScenarioParams.model_fields)
    assert all(p["unit"] and p["description"] for p in described)
    diesel = next(p for p in described if p["name"] == "diesel_price")
    assert diesel == {"name": "diesel_price", "unit": "USD/l", "required": False, "default": 1.43,
                      "description": "Diesel price in end_year.", "constraints": {"minimum": 0}}


CALIB = {"start_year": 2024, "pop_start_year": 1.15e6, "urban_ratio_start_year": 0.78,
         "grid_elec_ratio_start_year": 0.65, "grid_urban_elec_ratio": 0.8, "grid_rural_elec_ratio": 0.2}


def test_calibration_defaults_match_notebook():
    p = op.CalibrationParams.model_validate(CALIB).model_dump()
    # 1. OnSSET_Calibration.ipynb, cells 14-15
    assert (p["min_night_lights"], p["min_pop"], p["max_mv_line_distance"], p["max_transformer_dist"],
            p["max_hv_dist"]) == (0, 50, 2, 1, 5)
    assert (p["mg_dist"], p["mg_ntl"], p["mg_pop"]) == (0.5, 0, 0)


@pytest.mark.parametrize("override, message", [
    ({"urban_ratio_start_year": 1}, "urban_ratio_start_year"),
    ({"grid_elec_ratio_start_year": 1.2}, "grid_elec_ratio_start_year"),
    ({"mg_dist": -1}, "mg_dist"),
    ({"unknown": 1}, "unknown"),
])
def test_invalid_calibration_params(override, message):
    with pytest.raises(ValueError, match=message):
        op.CalibrationParams.model_validate({**CALIB, **override})


def test_describe_calibration_parameters():
    groups = op.describe_parameters(op.CalibrationParams)
    assert set(groups) == {"statistics", "grid_calibration", "mini_grid_calibration"}
