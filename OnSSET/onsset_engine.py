"""Headless OnSSET scenario engine.

Port of the logic in the OnSSET notebooks (``2. OnSSET_Scenarios.ipynb``,
``funcs.ipynb`` and ``detailed_tech_parameters.ipynb``) into a plain module:
no Tkinter dialogs, no plots, all inputs passed explicitly.

The OnSSET library prints progress to stdout, so MCP servers must run this
engine in a subprocess (see ``main``) rather than in-process over stdio.

    python onsset_engine.py --input-csv ... --pv-csv ... --wind-csv ... \
        --mv-lines ... --params params.json --output-dir out --scenario-name s1
"""

import argparse
import json
import logging
import os
import re
import sys
import time

import geojson
import geopandas as gpd
import numpy as np
import pandas as pd
from onsset import (SET_ELEC_FINAL_CODE, SET_ELEC_POP, SET_HH_DEMAND, SET_INVESTMENT_COST, SET_LCOE_GRID,
                    SET_MG_DIESEL_FUEL, SET_MIN_GRID_DIST, SET_NEW_CAPACITY, SET_NEW_CONNECTIONS, SET_POP,
                    SET_SA_DIESEL_FUEL, SET_X_DEG, SET_Y_DEG, SettlementProcessor, Technology)

from onsset_params import ScenarioParams

logger = logging.getLogger("onsset_engine")

TECH_LABELS = {1: "Grid_dens", 2: "Grid_ext", 3: "SA_PV", 5: "MG_PV_Hybrid", 6: "MG_Wind", 7: "MG_Hydro",
               99: "Non-electrified"}


def resolve_params(params):
    """Validate user params against ScenarioParams and return the full parameter dict."""
    return ScenarioParams.model_validate(params).model_dump()


def time_horizon(p):
    """Return (years_of_analysis, eleclimits, time_steps) as the notebooks build them."""
    eleclimits = {**p["intermediate_targets"], p["end_year"]: p["end_electrification_rate_target"]}
    years = sorted(eleclimits)
    time_steps = {y: y - (years[i - 1] if i else p["start_year"]) for i, y in enumerate(years)}
    return years, eleclimits, time_steps


def build_tech_info(p):
    """Port of ``init_tech_info`` from detailed_tech_parameters.ipynb."""
    grid_calc = Technology(om_of_td_lines=0.02,
                           distribution_losses=p["grid_losses"],
                           connection_cost_per_hh=100,
                           capacity_factor=1,
                           tech_life=30,
                           grid_capacity_investment=p["grid_power_plants_capital_cost"],
                           grid_price=p["grid_generation_cost"],
                           discount_rate=p["grid_discount_rate"],
                           mv_line_type=p["grid_mv_line_capacity"],
                           mv_line_amperage_limit=p["grid_MV_line_amperage_limit"],
                           mv_line_cost=p["grid_mv_line_cost"],
                           lv_line_type=p["grid_lv_line_capacity"],
                           lv_line_cost=p["grid_lv_line_cost"],
                           lv_line_max_length=p["grid_lv_line_max_length"],
                           service_transf_type=p["grid_service_Transf_type"],
                           service_transf_cost=p["grid_service_Transf_cost"],
                           max_nodes_per_serv_trans=p["grid_max_nodes_per_serv_trans"],
                           cnse=p["cnse"])

    mg_network = dict(om_of_td_lines=0.02,
                      distribution_losses=0.05,
                      connection_cost_per_hh=100,
                      capacity_factor=0.5,
                      discount_rate=p["mini_grid_discount_rate"],
                      mv_line_type=p["mg_mv_line_capacity"],
                      mv_line_amperage_limit=p["mg_MV_line_amperage_limit"],
                      mv_line_cost=p["mg_mv_line_cost"],
                      lv_line_type=p["mg_lv_line_capacity"],
                      lv_line_cost=p["mg_lv_line_cost"],
                      lv_line_max_length=p["mg_lv_line_max_length"],
                      service_transf_type=p["mg_service_Transf_type"],
                      service_transf_cost=p["mg_service_Transf_cost"],
                      max_nodes_per_serv_trans=p["mg_max_nodes_per_serv_trans"])

    mg_pv_hybrid_calc = Technology(tech_life=20, mini_grid=True, hybrid=True, **mg_network)
    mg_wind_hybrid_calc = Technology(tech_life=20, mini_grid=True, hybrid=True, **mg_network)
    mg_hydro_calc = Technology(tech_life=30, capital_cost={float("inf"): p["mg_hydro_capital_cost"]},
                               om_costs=0.02, **mg_network)

    sa_pv_calc = Technology(base_to_peak_load_ratio=0.9,
                            tech_life=p["shs_lifetime"],
                            om_costs=0.05,
                            discount_rate=p["standalone_discount_rate"],
                            capital_cost={0.020: p["sa_pv_capital_cost_1"],
                                          0.050: p["sa_pv_capital_cost_2"],
                                          0.100: p["sa_pv_capital_cost_3"],
                                          1: p["sa_pv_capital_cost_4"],
                                          float("inf"): p["sa_pv_capital_cost_5"]},
                            standalone=True)

    battery = {
        "n_chg": 0.92,  # charge efficiency of battery
        "n_dis": 0.92,  # discharge efficiency of battery
        "battery_cost": p["battery_cost"],
        "charge_controller": 0,  # included in pv_cost
        "diesel_life": p["diesel_life"],
        "diesel_om": 0.1,
        "battery_inverter_cost": p["inverter_cost"],
        "battery_inverter_life": p["inverter_life"],
        "dod_max": 0.8,  # maximum depth of discharge of battery
        "inv_eff": 0.93,  # inverter efficiency
        "lpsp_max": p["lpsp_max"],
        "full_life_cycles": 2000,  # equivalent full battery cycles until replacement
        "min_mg_connections": p["min_mg_size"],
        "diesel_cost": p["diesel_gen_cost"],
        "discount_rate": p["mini_grid_discount_rate"],
    }
    mg_pv_hybrid_params = {**battery,
                           "pv_cost": p["pv_cost"],
                           "pv_inverter": 0,  # included in pv_cost
                           "pv_life": p["pv_life"],
                           "pv_om": 0.015,
                           "diesel_limit": p["max_diesel"]}
    mg_wind_hybrid_params = {**battery,
                             "wind_cost": p["wind_cost"],
                             "wind_life": 25,
                             "wind_om": 0.015,
                             "diesel_limit": 0.7}

    mg_diesel_params = {"diesel_price": p["diesel_price"],
                        "efficiency": 0.33,
                        "diesel_truck_consumption": 33.7,
                        "diesel_truck_volume": 15000}

    # Stand-alone diesel generator specs - for grid backup
    sa_diesel_calc = Technology(base_to_peak_load_ratio=0.9,
                                capacity_factor=0.7,
                                tech_life=10,
                                om_costs=0.1,
                                capital_cost=938,
                                diesel_price=p["diesel_price"],
                                standalone=True,
                                efficiency=0.28,
                                diesel_truck_consumption=14,
                                diesel_truck_volume=300)

    return dict(grid_calc=grid_calc, mg_pv_hybrid_calc=mg_pv_hybrid_calc, mg_wind_hybrid_calc=mg_wind_hybrid_calc,
                mg_hydro_calc=mg_hydro_calc, sa_pv_calc=sa_pv_calc, sa_diesel_calc=sa_diesel_calc,
                mg_pv_hybrid_params=mg_pv_hybrid_params, mg_wind_hybrid_params=mg_wind_hybrid_params,
                mg_diesel_params=mg_diesel_params)


def load_settlements(input_csv):
    onsseter = SettlementProcessor(input_csv)
    onsseter.conditioning()
    return onsseter


def grid_start_points(onsseter, mv_lines):
    """Existing MV line vertices plus currently grid-connected settlements (notebook cells 6-8)."""
    x_mv, y_mv = onsseter.start_extension_points(mv_lines)
    code_col = max((c for c in onsseter.df.columns if re.fullmatch(rf"{SET_ELEC_FINAL_CODE}\d{{4}}", c)),
                   key=lambda c: int(c[-4:]))
    connected = onsseter.df[code_col] == 1
    x = np.append(x_mv, onsseter.df.loc[connected, SET_X_DEG].to_numpy())
    y = np.append(y_mv, onsseter.df.loc[connected, SET_Y_DEG].to_numpy())
    return x, y


def run_scenario(onsseter, p, tech, x_coordinates, y_coordinates, pv_csv, wind_csv):
    """Port of ``run_scenario`` from funcs.ipynb. Returns the new MV lines per year."""
    years, eleclimits, time_steps = time_horizon(p)
    start_year, end_year = p["start_year"], p["end_year"]
    auto_intensification = p["auto_intensification"]
    grid_calc, sa_diesel_calc = tech["grid_calc"], tech["sa_diesel_calc"]
    mg_diesel_params = tech["mg_diesel_params"]

    x_coords = x_coordinates * 1
    y_coords = y_coordinates * 1
    onsseter.df[SET_HH_DEMAND] = 0

    techs = ["Grid", "SA_PV", "MG_PVHybrid", "MG_Wind", "MG_Hydro"]
    tech_codes = [1, 3, 5, 6, 7]
    tiers = {i: p[f"tier_{i}"] for i in range(1, 6)}

    onsseter.project_pop_and_urban(p["end_year_pop"], p["urban_ratio_end_year"], start_year, years)
    onsseter.prepare_wtf_tier_columns(*tiers.values())
    onsseter.current_mv_line_dist()
    onsseter.add_xy_3395()
    try:
        onsseter.df.reset_index(inplace=True)
    except ValueError:
        pass

    Technology.set_default_values(base_year=start_year, start_year=start_year, end_year=end_year,
                                  hv_line_type=p["hv_line_capacity"], hv_line_cost=p["hv_line_cost"],
                                  hv_mv_sub_station_cost=p["hv_mv_transformer_cost"],
                                  hv_mv_substation_type=p["hv_mv_transformer_type"])

    new_lines_geojson = {}
    for year in years:
        eleclimit = eleclimits[year]
        time_step = time_steps[year]
        grid_connect_limit = time_step * p["annual_new_grid_connections_limit"]
        grid_cap_gen_limit = time_step * p["annual_grid_cap_gen_limit"] * 1000

        logger.info("%s: demand", year)
        # Keywords on purpose: the notebook passes urban/rural household sizes positionally in swapped order.
        onsseter.calculate_demand(year, num_people_per_hh_rural=p["num_people_per_hh_rural"],
                                  num_people_per_hh_urban=p["num_people_per_hh_urban"], time_step=time_step,
                                  urban_tier=p["urban_target_tier"], rural_tier_large=p["rural_target_tier_large"],
                                  rural_tier_small=p["rural_target_tier_small"], rural_cutoff=p["rural_cutoff_size"],
                                  tiers=tiers)
        onsseter.calculate_unmet_demand(year, reliability=p["grid_reliability"])

        for col in (SET_MG_DIESEL_FUEL, SET_SA_DIESEL_FUEL):
            onsseter.df.drop(columns=f"{col}{year}", errors="ignore", inplace=True)
        onsseter.diesel_cost_columns(mg_diesel_params, mg_diesel_params, year)
        fuel_col = f"{SET_MG_DIESEL_FUEL}{year}"
        onsseter.df[fuel_col] = onsseter.df[fuel_col].fillna(onsseter.df[fuel_col].mean())

        logger.info("%s: optimize wind hybrid mini-grids", year)
        lcoe, capacity, investment, _ = onsseter.wind_hybrids_lcoe_lookuptable(
            year, time_step, end_year, tech["mg_wind_hybrid_params"], wind_path=wind_csv)
        tech["mg_wind_hybrid_calc"].hybrid_fuel = lcoe
        tech["mg_wind_hybrid_calc"].hybrid_investment = investment.fillna(0)
        tech["mg_wind_hybrid_calc"].hybrid_capacity = capacity.fillna(0)

        logger.info("%s: optimize PV hybrid mini-grids", year)
        lcoe, capacity, investment, _ = onsseter.pv_hybrids_lcoe_lookuptable(
            year, time_step, end_year, tech["mg_pv_hybrid_params"], pv_path=pv_csv)
        tech["mg_pv_hybrid_calc"].hybrid_fuel = lcoe
        tech["mg_pv_hybrid_calc"].hybrid_investment = investment.fillna(0)
        tech["mg_pv_hybrid_calc"].hybrid_capacity = capacity.fillna(0)

        logger.info("%s: off-grid LCOEs", year)
        sa_pv_investment, sa_pv_capacity, mg_pv_hybrid_investment, mg_pv_hybrid_capacity, mg_wind_investment, \
            mg_wind_capacity, mg_hydro_investment, mg_hydro_capacity = onsseter.calculate_off_grid_lcoes(
                tech["mg_hydro_calc"], tech["mg_wind_hybrid_calc"], tech["sa_pv_calc"], tech["mg_pv_hybrid_calc"],
                year, end_year, time_step, techs, tech_codes, p["min_mg_size"], p["mg_min_grid_dist"])

        logger.info("%s: grid LCOEs and extension", year)
        grid_investment, grid_capacity, grid_cap_gen_limit, grid_connect_limit = onsseter.pre_electrification(
            p["grid_generation_cost"], year, time_step, end_year, grid_calc, sa_diesel_calc,
            p["grid_reliability_option"], grid_cap_gen_limit, grid_connect_limit)
        onsseter.max_extension_dist(year, time_step, end_year, start_year, grid_calc, sa_diesel_calc,
                                    p["grid_reliability_option"], p["max_grid_intensification_cost"],
                                    auto_intensification=auto_intensification)
        onsseter.pre_selection(eleclimit, year, time_step, auto_intensification, p["prio_choice"])

        onsseter.df[f"{SET_LCOE_GRID}{year}"], onsseter.df[f"{SET_MIN_GRID_DIST}{year}"], \
            grid_investment, grid_capacity, x_coords, y_coords, new_lines_geojson[year] = \
            onsseter.elec_extension_numba(grid_calc, mg_diesel_params, p["grid_reliability_option"],
                                          p["grid_mv_line_max_length"], year, end_year, time_step,
                                          grid_cap_gen_limit, grid_connect_limit, x_coords, y_coords,
                                          mg_interconnection=p["mg_interconnection"])

        logger.info("%s: results columns", year)
        onsseter.results_columns(techs, tech_codes, year, time_step, auto_intensification, p["mg_interconnection"])
        onsseter.calculate_investments_and_capacity(sa_pv_investment, sa_pv_capacity, mg_pv_hybrid_investment,
                                                    mg_pv_hybrid_capacity, mg_wind_investment, mg_wind_capacity,
                                                    mg_hydro_investment, mg_hydro_capacity, grid_investment,
                                                    grid_capacity, year)
        onsseter.check_grid_limitations(time_step * p["annual_new_grid_connections_limit"],
                                        time_step * p["annual_grid_cap_gen_limit"] * 1000,
                                        year, time_step, year == years[-1])
        onsseter.apply_limitations(eleclimit, year, time_step, auto_intensification)
        onsseter.calculate_emission(grid_factor=p["grid_emission_factor"], year=year,
                                    time_step=time_step, start_year=start_year)

        code_col = f"{SET_ELEC_FINAL_CODE}{year}"
        onsseter.df.loc[(onsseter.df[code_col] == 1) & (onsseter.df[f"{SET_ELEC_FINAL_CODE}{start_year}"] != 1),
                        code_col] = 2

    return new_lines_geojson


def finalize_results(onsseter, years):
    """Port of ``finalize_results`` from funcs.ipynb (non-simplified branch)."""
    df = onsseter.df
    for year in years:
        df.loc[df[f"{SET_ELEC_FINAL_CODE}{year}"] == 2, f"Technology{year}"] = "Grid extension"

    drop = ["NewDist", "GridCapacityRequired", "X", "Y", "minTDdist", "MVConnectDist", "MaxDist",
            "AverageToPeakLoadRatio", "level_0", "index", "MaxIntensificationDist"]
    drop += [f"ResidentialDemandTier{i}" for i in range(1, 6)]
    for year in years:
        drop += [f"{n}{year}" for n in ("PreSelection", "GridCapacityRequired", "PVHybridEmissionFactor",
                                        "UnmetDemand", "FilterLCOE", "MaxDist", "MaxIntensificationDist",
                                        "SADieselFuelCost", "windHybridEmissionFactor", "windHybridGenLCOE",
                                        "MGDieselFuelCost", "PVHybridGenLCOE", "Off_Grid_Code",
                                        "NoExtensionInvestment")]
        drop += [f"FilterLCOE{year}_1", f"NoExtensionInvestment{year}_1"]
    df.drop(columns=drop, errors="ignore", inplace=True)

    for i in range(len(df.columns)):
        if df.iloc[:, i].dtype == "float64":
            df.iloc[:, i] = pd.to_numeric(df.iloc[:, i], downcast="float")
        elif df.iloc[:, i].dtype == "int64":
            df.iloc[:, i] = pd.to_numeric(df.iloc[:, i], downcast="signed")


def summary_table(df, years):
    """Port of ``calc_summary_table``. Emissions are annual, in ktCO2 (the notebook mislabels them tCO2)."""
    codes = [1, 2, 3, 5, 6, 7, 99]
    columns = {}
    for year in years:
        code = df[f"{SET_ELEC_FINAL_CODE}{year}"]
        by_code = {c: code == c for c in codes}
        pop, conn = [], []
        cap, inv, em = [], [], []
        for c in codes:
            if c == 99:
                pop.append(int(df[f"{SET_POP}{year}"].sum() - df[f"{SET_ELEC_POP}{year}"].sum()))
                conn.append(0)
                cap.append(0.0), inv.append(0.0), em.append(0.0)
                continue
            m = by_code[c]
            pop.append(int(df.loc[m, f"{SET_POP}{year}"].sum()))
            conn.append(int(df.loc[m, f"{SET_NEW_CONNECTIONS}{year}"].sum()))
            cap.append(round(df.loc[m, f"{SET_NEW_CAPACITY}{year}"].sum() / 1000, 2))
            inv.append(round(df.loc[m, f"{SET_INVESTMENT_COST}{year}"].sum() / 1e6, 2))
            em.append(round(df.loc[m, f"AnnualEmissions{year}"].sum() / 1e6, 2))
        for name, vals in ((f"Population{year}", pop), (f"NewConnections{year}", conn),
                           (f"Capacity{year} (MW)", cap), (f"Investment{year} (million USD)", inv),
                           (f"Emissions{year} (ktCO2)", em)):
            columns[name] = vals + [sum(vals)]
    table = pd.DataFrame(columns, index=[TECH_LABELS[c] for c in codes] + ["Total"])

    if len(years) > 1:
        last = years[-1]
        table["PopulationTotal"] = table[f"Population{last}"]
        for metric, label in (("NewConnections", "NewConnectionsTotal"), ("Capacity", "CapacityTotal (MW)"),
                              ("Investment", "InvestmentTotal (million USD)"),
                              ("Emissions", "EmissionsTotal (ktCO2)")):
            table[label] = table[[c for c in table.columns if c.startswith(f"{metric}20")]].sum(axis=1)
    return table


def electrification_rates(df, years):
    return {year: float(df[f"{SET_ELEC_POP}{year}"].sum() / df[f"{SET_POP}{year}"].sum()) for year in years}


def start_year_stats(df):
    pop = df["PopStartYear"].sum()
    return {"population": float(pop),
            "electrification_rate": float(df["ElecPopCalib"].sum() / pop),
            "urban_ratio": float(df.loc[df["IsUrban"] == 2, "PopStartYear"].sum() / pop)}


def write_mv_lines(new_lines_geojson, output_dir, scenario_name):
    """Write new MV lines per year as EPSG:4326 GeoJSON (notebook cell 46)."""
    paths = {}
    for year, lines in new_lines_geojson.items():
        path = os.path.join(output_dir, f"new_mv_lines_{scenario_name}_{year}.geojson")
        with open(path, "w") as f:
            geojson.dump(lines, f)
        gdf = gpd.read_file(path).set_crs(3395, allow_override=True).to_crs(4326)
        os.remove(path)
        gdf.to_file(path, driver="GeoJSON")
        paths[year] = path
    return paths


def run(input_csv, pv_csv, wind_csv, mv_lines, params, output_dir, scenario_name):
    """Run one OnSSET scenario end to end and write its outputs to ``output_dir``.

    Returns a JSON-serialisable dict with the summary table, electrification
    rates, timing and output file paths.
    """
    t0 = time.time()
    p = resolve_params(params)
    years, _, _ = time_horizon(p)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Loading settlements from %s", input_csv)
    onsseter = load_settlements(input_csv)
    x, y = grid_start_points(onsseter, mv_lines)
    start_stats = start_year_stats(onsseter.df)
    t_loaded = time.time()

    new_lines = run_scenario(onsseter, p, build_tech_info(p), x, y, pv_csv, wind_csv)
    finalize_results(onsseter, years)
    t_run = time.time()

    table = summary_table(onsseter.df, years)
    rates = electrification_rates(onsseter.df, years)

    prefix = os.path.join(output_dir, scenario_name)
    files = {"results": f"{prefix}_Results.csv",
             "summary": f"{prefix}_Summaries.csv",
             "params": f"{prefix}_Params.json"}
    table.to_csv(files["summary"], index=True)
    with open(files["params"], "w") as f:
        json.dump({"scenario_name": scenario_name,
                   "inputs": {"input_csv": input_csv, "pv_csv": pv_csv, "wind_csv": wind_csv, "mv_lines": mv_lines},
                   "params": p, "start_year_stats": start_stats}, f, indent=2)
    onsseter.df.to_csv(files["results"], float_format="%.4f", index=False)
    files["new_mv_lines"] = write_mv_lines(new_lines, output_dir, scenario_name)

    return {"status": "success",
            "scenario_name": scenario_name,
            "years": years,
            "start_year_stats": start_stats,
            "electrification_rate": rates,
            "summary": json.loads(table.to_json(orient="index")),
            "files": files,
            "timing_s": {"load": round(t_loaded - t0, 1), "model": round(t_run - t_loaded, 1),
                         "total": round(time.time() - t0, 1)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input-csv", required=True, help="Calibrated OnSSET settlement CSV")
    ap.add_argument("--pv-csv", required=True, help="Hourly PV (renewables.ninja) CSV")
    ap.add_argument("--wind-csv", required=True, help="Hourly wind (renewables.ninja) CSV")
    ap.add_argument("--mv-lines", required=True, help="Existing MV lines (shapefile/GeoPackage/GeoJSON)")
    ap.add_argument("--params", required=True, help="JSON file with scenario parameters")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--scenario-name", required=True)
    ap.add_argument("--result-json", help="Where to write the run() result (default: <output-dir>/<scenario>_Run.json)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stderr)
    with open(args.params) as f:
        params = json.load(f)
    result_json = args.result_json or os.path.join(args.output_dir, f"{args.scenario_name}_Run.json")
    try:
        result = run(args.input_csv, args.pv_csv, args.wind_csv, args.mv_lines, params,
                     args.output_dir, args.scenario_name)
    except Exception as e:
        logger.exception("Scenario failed")
        result = {"status": "error", "scenario_name": args.scenario_name, "message": f"{type(e).__name__}: {e}"}
    os.makedirs(os.path.dirname(os.path.abspath(result_json)), exist_ok=True)
    with open(result_json, "w") as f:
        json.dump(result, f, indent=2)
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
