"""Input checks for the OnSSET workflows, derived from what the OnSSET code reads.

Each check returns ``{"path", "role", "ok", "errors", "warnings", "info"}``. Errors are things
that make the run fail or silently wrong; warnings are what OnSSET would patch over itself
(``SettlementProcessor.conditioning`` fills missing columns with 0 or 9999).

Nothing here imports ``onsset`` (it prints to stdout, which is the MCP channel), and the
column lists below mirror ``onsset/onsset.py`` at commit 486c260.
"""

import re

import numpy as np
import pandas as pd

# SettlementProcessor.conditioning(): columns it fills when absent, and with what.
CONDITIONING_FILL_9999 = ["PlannedHVLineDist", "SubstationDist", "PlannedMVLineDist", "CurrentMVLineDist",
                          "TransformerDist", "HydropowerDist", "HydropowerFID"]
CONDITIONING_FILL_0 = ["Country", "ElecPop", "IsUrban", "NightLights", "TravelHours", "WindVel",
                       "ResidentialDemandTierCustom", "CurrentHVLineDist", "Admin_1", "Hydropower", "HealthDemand",
                       "EducationDemand", "AgriDemand", "CommercialDemand", "RoadDist", "MGDist"]
# conditioning() only reports nulls in these ("Check the input file!") and leaves them in place.
NO_NULLS = ["GridCellArea", "Pop", "id", "X_deg", "Y_deg", "PlannedHVLineDist", "SubstationDist",
            "PlannedMVLineDist", "CurrentMVLineDist", "TransformerDist"]

# Read before conditioning() can fill anything: the constructor needs GHI, the routing needs
# coordinates, the LCOE functions need the cell area and population.
BASE_REQUIRED = ["id", "X_deg", "Y_deg", "Pop", "GridCellArea", "GHI"]
# Written by the calibration notebook (calibrate_current_pop_and_urban, calibrate_grid_elec_current,
# calc_wind_cfs) and read by the scenario run.
CALIBRATED_REQUIRED = ["PopStartYear", "ElecPopCalib", "ElecStart", "IsUrban", "WindCF"]
FINAL_CODES = {1, 2, 3, 5, 6, 7, 99}

PV_SKIPROWS = 341882  # onsset.hybrids.read_environmental_data default
PV_TEMP_COL, PV_GHI_COL = 2, 3
WIND_SKIPROWS, WIND_COL = 3, 3  # onsset.hybrids_wind.read_wind_environmental_data defaults
HOURS = 8760


def _report(path, role):
    return {"path": str(path), "role": role, "ok": True, "errors": [], "warnings": [], "info": {}}


def _finish(report):
    report["ok"] = not report["errors"]
    return report


def read_header(path):
    """Columns and separator as SettlementProcessor reads them (',' unless GHI is only found with ';')."""
    columns = list(pd.read_csv(path, nrows=0).columns)
    if "GHI" not in columns:
        semi = list(pd.read_csv(path, nrows=0, sep=";").columns)
        if "GHI" in semi:
            return semi, ";"
    return columns, ","


def year_columns(columns, prefix):
    return sorted(int(m.group(1)) for c in columns if (m := re.fullmatch(rf"{prefix}(\d{{4}})", c)))


def validate_settlements(path, workflow="scenario", start_year=None, mg_dist=None, needs_custom_tier=False):
    """Check a settlement CSV for the calibration or the scenario workflow.

    ``needs_custom_tier``: a target tier is 6, so the per-settlement ResidentialDemandTierCustom is used.
    """
    report = _report(path, f"settlements ({workflow})")
    errors, warnings, info = report["errors"], report["warnings"], report["info"]
    try:
        columns, sep = read_header(path)
    except Exception as e:  # noqa: BLE001 - any parse failure is a bad input file
        errors.append(f"Cannot read CSV header: {type(e).__name__}: {e}")
        return _finish(report)
    info["separator"] = sep
    info["n_columns"] = len(columns)

    required = list(BASE_REQUIRED)
    final_years = year_columns(columns, "FinalElecCode")
    info["final_elec_code_years"] = final_years
    if workflow == "scenario":
        required += CALIBRATED_REQUIRED
        if start_year is None:
            start_year = final_years[-1] if final_years else None
            info["start_year_inferred"] = start_year
        if start_year is not None:
            required += [f"FinalElecCode{start_year}", f"ElecPop{start_year}"]
            if final_years and final_years[-1] != start_year:
                warnings.append(f"The latest FinalElecCode column is {final_years[-1]} but start_year is "
                                f"{start_year}. The engine (like the notebook) seeds the grid from the latest one.")
        else:
            errors.append("No FinalElecCode<year> column: the file is not calibrated. Run the calibration first.")
    else:
        if not {"TransformerDist", "CurrentMVLineDist", "CurrentHVLineDist"} & set(columns):
            errors.append("Calibration needs at least one of TransformerDist, CurrentMVLineDist, CurrentHVLineDist.")
        if "NightLights" not in columns:
            errors.append("Calibration needs NightLights (settlements with no light get no calibrated "
                          "electrified population).")
        if "MGDist" not in columns and (mg_dist is None or mg_dist > 0):
            errors.append("MGDist is missing: OnSSET would fill it with 0, which marks every settlement without "
                          "grid access as mini-grid electrified. Add MGDist or set mg_dist to 0.")

    if needs_custom_tier:
        required.append("ResidentialDemandTierCustom")
    missing = [c for c in dict.fromkeys(required) if c not in columns]
    if missing:
        errors.append(f"Missing required columns: {missing}")
    for c in CONDITIONING_FILL_9999:
        if c not in columns:
            warnings.append(f"{c} is missing; OnSSET fills it with 9999 (treated as very far).")
    filled_zero = [c for c in CONDITIONING_FILL_0 if c not in columns and not (workflow == "calibration" and
                                                                                c == "MGDist")]
    if filled_zero:
        warnings.append(f"Missing columns OnSSET fills with 0: {filled_zero}")

    check = [c for c in dict.fromkeys(required + NO_NULLS + ["IsUrban"]) if c in columns]
    try:
        df = pd.read_csv(path, sep=sep, usecols=check, low_memory=False)
    except Exception as e:  # noqa: BLE001
        errors.append(f"Cannot read CSV data: {type(e).__name__}: {e}")
        return _finish(report)
    info["n_settlements"] = int(len(df))
    if df.empty:
        errors.append("The file has no rows.")
        return _finish(report)

    numeric = df.apply(pd.to_numeric, errors="coerce")
    for c in check:
        bad = int((numeric[c].isna() & df[c].notna()).sum())
        if bad:
            errors.append(f"{c}: {bad} non-numeric values.")
        nulls = int(df[c].isna().sum())
        if nulls and c in required + NO_NULLS:
            errors.append(f"{c}: {nulls} empty values (OnSSET does not fill this column).")
    if "id" in df and df["id"].duplicated().any():
        errors.append(f"id: {int(df['id'].duplicated().sum())} duplicated settlement ids.")
    if "X_deg" in numeric and not numeric["X_deg"].between(-180, 180).all():
        errors.append("X_deg has values outside [-180, 180]; coordinates must be WGS84 degrees.")
    if "Y_deg" in numeric and not numeric["Y_deg"].between(-90, 90).all():
        errors.append("Y_deg has values outside [-90, 90]; coordinates must be WGS84 degrees.")
    for c in ("Pop", "GridCellArea", "PopStartYear", "ElecPopCalib"):
        if c in numeric and (numeric[c] < 0).any():
            errors.append(f"{c} has negative values.")
    if "IsUrban" in numeric:
        values = set(numeric["IsUrban"].dropna().unique())
        if workflow == "scenario" and not values <= {0, 1, 2}:
            errors.append(f"IsUrban must be 0 (rural), 1 or 2 (urban); found {sorted(values)[:10]}.")
        if workflow == "scenario" and 2 not in values:
            errors.append("No urban settlement (IsUrban == 2): the urban growth rate is undefined.")
    code_col = f"FinalElecCode{start_year}"
    if workflow == "scenario" and code_col in numeric:
        values = set(numeric[code_col].dropna().astype(int).unique())
        if not values <= FINAL_CODES:
            errors.append(f"{code_col} has codes outside {sorted(FINAL_CODES)}: {sorted(values - FINAL_CODES)}")
        if 1 not in values:
            warnings.append(f"No settlement is grid connected in {code_col}; the grid can only start from the "
                            "MV lines.")
    if workflow == "scenario" and {"PopStartYear", "ElecPopCalib", "IsUrban"} <= set(numeric):
        pop = float(numeric["PopStartYear"].sum())
        if pop > 0:
            info["start_year_population"] = pop
            info["start_year_electrification_rate"] = float(numeric["ElecPopCalib"].sum() / pop)
            info["start_year_urban_ratio"] = float(numeric.loc[numeric["IsUrban"] == 2, "PopStartYear"].sum() / pop)
        else:
            errors.append("PopStartYear sums to 0.")
    return _finish(report)


def _count_lines(path):
    with open(path, "rb") as f:
        return sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))


def validate_pv(path):
    """Hourly PV weather CSV as read by ``read_environmental_data``: rows after line 341882, column 2
    temperature (degC), column 3 surface irradiance. That offset selects the last year of the 1980-2019
    renewables.ninja country weather file."""
    report = _report(path, "pv_hourly")
    errors, info = report["errors"], report["info"]
    lines = _count_lines(path)
    info["lines"] = lines
    rows = lines - PV_SKIPROWS - 1  # the line after the skipped block is consumed as header
    if rows < HOURS:
        errors.append(f"OnSSET skips the first {PV_SKIPROWS} lines of the PV file and reads the next {HOURS} "
                      f"hours; this file has {lines} lines. Use the renewables.ninja country weather file "
                      "(hourly, 1980-2019).")
        return _finish(report)
    if rows > HOURS:
        report["warnings"].append(f"{rows} hourly rows follow the skipped block, {HOURS} expected; OnSSET uses "
                                  "all of them as one year.")
    try:
        data = pd.read_csv(path, usecols=[PV_TEMP_COL, PV_GHI_COL], skiprows=PV_SKIPROWS, header=None, nrows=rows + 1)
    except Exception as e:  # noqa: BLE001
        errors.append(f"Cannot read PV columns {PV_TEMP_COL} and {PV_GHI_COL}: {type(e).__name__}: {e}")
        return _finish(report)
    data = data.iloc[1:].apply(pd.to_numeric, errors="coerce")
    if data.isna().any().any():
        errors.append("Temperature or irradiance has non-numeric values in the year OnSSET reads.")
    else:
        ghi = data[PV_GHI_COL]
        info["hours"] = int(len(data))
        info["irradiance_sum"] = float(ghi.sum())
        info["temperature_mean_c"] = float(data[PV_TEMP_COL].mean())
        if ghi.sum() <= 0 or (ghi < 0).any():
            errors.append("Irradiance must be non-negative and not all zero.")
    return _finish(report)


def validate_wind(path):
    """Hourly wind CSV as read by ``read_wind_environmental_data``: skip 3 lines, column 3 is wind speed (m/s)."""
    report = _report(path, "wind_hourly")
    errors, info = report["errors"], report["info"]
    try:
        data = pd.read_csv(path, usecols=[WIND_COL], skiprows=WIND_SKIPROWS)
    except Exception as e:  # noqa: BLE001
        errors.append(f"Cannot read column {WIND_COL} after skipping {WIND_SKIPROWS} lines: {type(e).__name__}: {e}. "
                      "Expected a renewables.ninja wind point file (3 comment lines, then "
                      "time,local_time,electricity,wind_speed).")
        return _finish(report)
    info["column"] = str(data.columns[0])
    speed = pd.to_numeric(data.iloc[:, 0], errors="coerce")
    info["hours"] = int(len(speed))
    if speed.isna().any():
        errors.append(f"Wind speed column '{data.columns[0]}' has non-numeric values.")
    elif len(speed) != HOURS:
        errors.append(f"Expected {HOURS} hourly wind speeds, found {len(speed)}.")
    else:
        info["mean_speed_ms"] = float(speed.mean())
        if speed.mean() <= 0:
            errors.append("Mean wind speed must be positive (OnSSET scales the curve by it).")
    if "wind" not in info["column"].lower():
        report["warnings"].append(f"Column 3 is '{info['column']}', not wind_speed.")
    return _finish(report)


def validate_mv_lines(path):
    """Existing MV network as read by ``SettlementProcessor.start_extension_points`` (any OGR vector)."""
    report = _report(path, "mv_lines")
    errors, info = report["errors"], report["info"]
    try:
        import geopandas as gpd  # heavy; only this check needs it
        gdf = gpd.read_file(path)
    except Exception as e:  # noqa: BLE001
        errors.append(f"Cannot read vector file: {type(e).__name__}: {e}")
        return _finish(report)
    info["features"] = int(len(gdf))
    info["crs"] = str(gdf.crs) if gdf.crs else None
    types = gdf.geom_type.value_counts().to_dict()
    info["geometry_types"] = {str(k): int(v) for k, v in types.items()}
    if gdf.empty:
        errors.append("The file has no features.")
    if gdf.crs is None:
        errors.append("No CRS defined; OnSSET reprojects the lines to EPSG:3395.")
    other = set(types) - {"LineString", "MultiLineString"}
    if other:
        errors.append(f"Only (Multi)LineString geometries are supported, found {sorted(other)}.")
    if gdf.geometry.isna().any() or gdf.geometry.is_empty.any():
        errors.append("Some features have empty geometries.")
    return _finish(report)


def check_bounds_overlap(settlements_path, mv_lines_path):
    """Warn when the MV lines do not overlap the settlements' bounding box (wrong country or CRS)."""
    try:
        import geopandas as gpd
        columns, sep = read_header(settlements_path)
        xy = pd.read_csv(settlements_path, sep=sep, usecols=["X_deg", "Y_deg"])
        lines = gpd.read_file(mv_lines_path).to_crs(4326)
    except Exception:  # noqa: BLE001 - the per-file checks report read errors
        return None
    minx, miny, maxx, maxy = lines.total_bounds
    overlaps = not (maxx < xy.X_deg.min() or minx > xy.X_deg.max() or maxy < xy.Y_deg.min() or
                    miny > xy.Y_deg.max())
    if not np.isfinite([minx, miny, maxx, maxy]).all() or overlaps:
        return None
    return "The MV lines do not overlap the settlements' extent; check that both cover the same country."
