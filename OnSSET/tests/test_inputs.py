"""Input validators on small synthetic files, plus the real Uganda inputs when present."""
import numpy as np
import pandas as pd
import pytest

import onsset_inputs as inputs
from conftest import HAVE_UGANDA, UGANDA_FILES


def settlements(**overrides):
    n = 6
    data = {"id": range(n), "X_deg": np.linspace(32, 33, n), "Y_deg": np.linspace(0, 1, n),
            "Pop": [100.0] * n, "GridCellArea": [1.0] * n, "GHI": [2000.0] * n, "IsUrban": [0, 0, 0, 0, 2, 2],
            "NightLights": [0, 1, 0, 2, 5, 9], "CurrentMVLineDist": [1.0] * n, "MGDist": [9.0] * n,
            "PopStartYear": [120.0] * n, "ElecPopCalib": [0, 0, 0, 0, 120, 120], "ElecStart": [0, 0, 0, 0, 1, 1],
            "WindCF": [0.1] * n, "FinalElecCode2024": [99, 99, 99, 99, 1, 1], "ElecPop2024": [0, 0, 0, 0, 120, 120]}
    data.update(overrides)
    return pd.DataFrame(data)


def write(df, path, **kw):
    df.to_csv(path, index=False, **kw)
    return path


def test_calibrated_settlements_pass(tmp_path):
    r = inputs.validate_settlements(write(settlements(), tmp_path / "s.csv"), "scenario", start_year=2024)
    assert r["ok"], r["errors"]
    assert r["info"]["n_settlements"] == 6
    assert r["info"]["start_year_electrification_rate"] == pytest.approx(240 / 720)
    assert r["info"]["start_year_urban_ratio"] == pytest.approx(240 / 720)


def test_start_year_inferred_from_latest_code_column(tmp_path):
    r = inputs.validate_settlements(write(settlements(), tmp_path / "s.csv"), "scenario")
    assert r["info"]["start_year_inferred"] == 2024 and r["ok"]


def test_semicolon_separator_detected_like_onsset(tmp_path):
    r = inputs.validate_settlements(write(settlements(), tmp_path / "s.csv", sep=";"), "scenario")
    assert r["ok"], r["errors"]
    assert r["info"]["separator"] == ";"


def test_uncalibrated_csv_rejected_for_scenario(tmp_path):
    df = settlements().drop(columns=["PopStartYear", "ElecPopCalib", "ElecStart", "WindCF", "FinalElecCode2024",
                                     "ElecPop2024"])
    r = inputs.validate_settlements(write(df, tmp_path / "s.csv"), "scenario")
    assert not r["ok"]
    assert any("not calibrated" in e for e in r["errors"])
    assert inputs.validate_settlements(tmp_path / "s.csv", "calibration")["ok"]


def test_wrong_start_year_reports_missing_columns(tmp_path):
    r = inputs.validate_settlements(write(settlements(), tmp_path / "s.csv"), "scenario", start_year=2020)
    assert any("FinalElecCode2020" in e for e in r["errors"])
    assert any("latest FinalElecCode column is 2024" in w for w in r["warnings"])


@pytest.mark.parametrize("override, message", [
    ({"Pop": [100, None, 100, 100, 100, 100]}, "Pop: 1 empty values"),
    ({"GHI": ["a", 1, 1, 1, 1, 1]}, "GHI: 1 non-numeric"),
    ({"id": [0, 0, 1, 2, 3, 4]}, "duplicated settlement ids"),
    ({"X_deg": [500.0] * 6}, "X_deg has values outside"),
    ({"IsUrban": [0] * 6}, "No urban settlement"),
    ({"FinalElecCode2024": [4, 99, 99, 99, 1, 1]}, "codes outside"),
    ({"Pop": [-1.0] * 6}, "Pop has negative"),
])
def test_bad_settlement_values(tmp_path, override, message):
    r = inputs.validate_settlements(write(settlements(**override), tmp_path / "s.csv"), "scenario", start_year=2024)
    assert not r["ok"]
    assert any(message in e for e in r["errors"]), r["errors"]


def test_missing_mgdist_blocks_calibration_unless_disabled(tmp_path):
    path = write(settlements().drop(columns=["MGDist"]), tmp_path / "s.csv")
    assert any("MGDist" in e for e in inputs.validate_settlements(path, "calibration", mg_dist=0.5)["errors"])
    assert inputs.validate_settlements(path, "calibration", mg_dist=0)["ok"]


def test_custom_tier_column_required_for_tier_6(tmp_path):
    path = write(settlements(), tmp_path / "s.csv")
    r = inputs.validate_settlements(path, "scenario", needs_custom_tier=True)
    assert any("ResidentialDemandTierCustom" in e for e in r["errors"])


def test_unreadable_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    assert not inputs.validate_settlements(path, "scenario")["ok"]


def pv_file(path, hours=inputs.HOURS, ghi=1.0):
    with open(path, "w") as f:
        f.write("# Renewables.ninja Weather\n# Units\n")
        f.write("time,precipitation,temperature,irradiance_surface,irradiance_toa\n")
        for i in range(inputs.PV_SKIPROWS - 3 + 1 + hours):
            f.write(f"t{i},0,20.0,{ghi},0\n")
    return path


def test_pv_layout(tmp_path):
    r = inputs.validate_pv(pv_file(tmp_path / "pv.csv"))
    assert r["ok"], r["errors"]
    assert r["info"]["hours"] == inputs.HOURS
    assert r["info"]["irradiance_sum"] == inputs.HOURS


def test_short_pv_file_rejected(tmp_path):
    path = tmp_path / "pv.csv"
    path.write_text("time,a,temperature,irradiance\n" + "x,0,20,1\n" * 8760)
    r = inputs.validate_pv(path)
    assert not r["ok"] and "1980-2019" in r["errors"][0]


def wind_file(path, speeds):
    lines = ["# Renewables.ninja Wind", "# Units", "# {}", "time,local_time,electricity,wind_speed"]
    lines += [f"t,t,0,{s}" for s in speeds]
    path.write_text("\n".join(lines) + "\n")
    return path


def test_wind_layout(tmp_path):
    r = inputs.validate_wind(wind_file(tmp_path / "w.csv", [3.0] * inputs.HOURS))
    assert r["ok"] and r["info"]["mean_speed_ms"] == 3.0


def test_wind_wrong_length(tmp_path):
    assert not inputs.validate_wind(wind_file(tmp_path / "w.csv", [3.0] * 100))["ok"]


def test_mv_lines(tmp_path):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import LineString, Point
    good = gpd.GeoDataFrame(geometry=[LineString([(32, 0), (33, 1)])], crs=4326)
    good.to_file(tmp_path / "mv.geojson", driver="GeoJSON")
    r = inputs.validate_mv_lines(tmp_path / "mv.geojson")
    assert r["ok"] and r["info"]["crs"] == "EPSG:4326"
    gpd.GeoDataFrame(geometry=[Point(32, 0)], crs=4326).to_file(tmp_path / "pt.geojson", driver="GeoJSON")
    assert any("LineString" in e for e in inputs.validate_mv_lines(tmp_path / "pt.geojson")["errors"])
    s = write(settlements(), tmp_path / "s.csv")
    assert inputs.check_bounds_overlap(s, tmp_path / "mv.geojson") is None
    far = gpd.GeoDataFrame(geometry=[LineString([(-70, 40), (-69, 41)])], crs=4326)
    far.to_file(tmp_path / "far.geojson", driver="GeoJSON")
    assert "do not overlap" in inputs.check_bounds_overlap(s, tmp_path / "far.geojson")


@pytest.mark.skipif(not HAVE_UGANDA, reason="Uganda inputs not available")
def test_real_uganda_inputs():
    r = inputs.validate_settlements(UGANDA_FILES["input_csv"], "scenario", start_year=2024)
    assert r["ok"], r["errors"]
    # The baseline notebook reports a modelled start-year electrification rate of 0.35024.
    assert r["info"]["start_year_electrification_rate"] == pytest.approx(0.3502401358731049)
    assert inputs.validate_pv(UGANDA_FILES["pv_csv"])["ok"]
    assert inputs.validate_wind(UGANDA_FILES["wind_csv"])["ok"]
    assert inputs.validate_mv_lines(UGANDA_FILES["mv_lines"])["ok"]
