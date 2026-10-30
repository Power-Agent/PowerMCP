"""Headless OnSSET calibration.

Port of ``1. OnSSET_Calibration.ipynb`` (cells 5, 12, 14, 15 and 21): calibrates the base-year
population, urban/rural split and current grid and mini-grid electrification of a GIS-extracted
settlement CSV, and writes the calibrated CSV that ``onsset_engine.py`` takes as input. No
Tkinter dialogs and no plots; like the engine it prints through OnSSET, so MCP servers run it
in a subprocess.

    python onsset_calibration.py --input-csv ... --params calib.json --output-dir out --name c1
"""

import argparse
import json
import logging
import os
import sys
import time

from onsset import (SET_ELEC_FINAL_CODE, SET_ELEC_POP, SET_ELEC_POP_CALIB, SET_POP, SET_POP_CALIB, SET_URBAN,
                    SET_WINDCF, SET_WINDVEL, SettlementProcessor)

from onsset_params import CalibrationParams

logger = logging.getLogger("onsset_calibration")

CALIBRATED_FILE = "OnSSET_InputFile_Calibrated.csv"


def calibrate(onsseter, p):
    """Calibrate ``onsseter.df`` in place. Returns the modelled base-year statistics."""
    start_year = p["start_year"]
    df = onsseter.df

    pop_modelled, urban_modelled = onsseter.calibrate_current_pop_and_urban(p["pop_start_year"],
                                                                            p["urban_ratio_start_year"])
    df[f"{SET_POP}{start_year}"] = df[SET_POP_CALIB]
    df[SET_WINDCF] = onsseter.calc_wind_cfs(df[SET_WINDVEL])

    grid_rate, rural_elec, urban_elec, dist_limit, *_ = onsseter.calibrate_grid_elec_current(
        p["grid_elec_ratio_start_year"], p["grid_urban_elec_ratio"], p["grid_rural_elec_ratio"], start_year,
        min_night_lights=p["min_night_lights"], min_pop=p["min_pop"], max_transformer_dist=p["max_transformer_dist"],
        max_mv_dist=p["max_mv_line_distance"], max_hv_dist=p["max_hv_dist"], buffer=False)

    # Notebook cell 15: existing mini-grids. The first block resets any code 5 left in the input.
    df = onsseter.df
    code = f"{SET_ELEC_FINAL_CODE}{start_year}"
    elec_pop = f"{SET_ELEC_POP}{start_year}"
    was_mg = df[code] == 5
    df.loc[was_mg, "ElecStart"] = 0
    df.loc[was_mg, code] = 99
    df.loc[was_mg, SET_ELEC_POP_CALIB] = 0
    df.loc[was_mg, elec_pop] = 0
    if p["mg_dist"] > 0:
        mg = (df[code] != 1) & (df["NightLights"] >= p["mg_ntl"]) & (df["MGDist"] < p["mg_dist"]) & \
             (df[f"{SET_POP}{start_year}"] > p["mg_pop"])
        df.loc[mg, "ElecStart"] = 1
        df.loc[mg, code] = 5
        df.loc[mg, SET_ELEC_POP_CALIB] = df.loc[mg, SET_POP_CALIB]
    df[elec_pop] = df[SET_ELEC_POP_CALIB]

    pop = float(df[SET_POP_CALIB].sum())
    return {"start_year": start_year,
            "population": pop,
            "urban_ratio": float(df.loc[df[SET_URBAN] == 2, SET_POP_CALIB].sum() / pop),
            "grid_electrification_rate": float(df.loc[df[code] == 1, SET_ELEC_POP_CALIB].sum() / pop),
            "mini_grid_electrification_rate": float(df.loc[df[code] == 5, SET_ELEC_POP_CALIB].sum() / pop),
            "electrification_rate": float(df[SET_ELEC_POP_CALIB].sum() / pop),
            "grid_calibration_distance_limit_km": float(dist_limit),
            "settlements": int(len(df)),
            "settlements_grid_connected": int((df[code] == 1).sum()),
            "settlements_mini_grid": int((df[code] == 5).sum()),
            "targets": {"population": p["pop_start_year"], "urban_ratio": p["urban_ratio_start_year"],
                        "grid_electrification_rate": p["grid_elec_ratio_start_year"]}}


def run(input_csv, params, output_dir, name):
    t0 = time.time()
    p = CalibrationParams.model_validate(params).model_dump()
    os.makedirs(output_dir, exist_ok=True)
    logger.info("Loading settlements from %s", input_csv)
    onsseter = SettlementProcessor(input_csv)
    onsseter.conditioning()
    stats = calibrate(onsseter, p)
    files = {"calibrated_csv": os.path.join(output_dir, CALIBRATED_FILE),
             "params": os.path.join(output_dir, f"{name}_CalibrationParams.json")}
    onsseter.df.to_csv(files["calibrated_csv"], float_format="%.4f", index=False)
    with open(files["params"], "w") as f:
        json.dump({"name": name, "input_csv": input_csv, "params": p}, f, indent=2)
    return {"status": "success", "kind": "calibration", "name": name, "calibration": stats, "files": files,
            "timing_s": {"total": round(time.time() - t0, 1)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-csv", required=True, help="GIS-extracted OnSSET settlement CSV")
    ap.add_argument("--params", required=True, help="JSON file with calibration parameters")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--result-json", help="Where to write the run() result (default: <output-dir>/<name>_Run.json)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
    with open(args.params) as f:
        params = json.load(f)
    result_json = args.result_json or os.path.join(args.output_dir, f"{args.name}_Run.json")
    try:
        result = run(args.input_csv, params, args.output_dir, args.name)
    except Exception as e:
        logger.exception("Calibration failed")
        result = {"status": "error", "kind": "calibration", "name": args.name,
                  "message": f"{type(e).__name__}: {e}"}
    os.makedirs(os.path.dirname(os.path.abspath(result_json)), exist_ok=True)
    with open(result_json, "w") as f:
        json.dump(result, f, indent=2)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
