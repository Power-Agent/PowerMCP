"""
Computes capacity cost ($/MW-day) for a completed GenX scenario period.
Mainly for use when the test system you are studying has a capacity market.
See the README for the formulas applied in the calculation.

By default every CapRes region and every demand zone in the case is included;
pass `capres_regions` / `zones` to restrict to a subset.
"""
import os

import numpy as np
import pandas as pd


def resolve_scenario(scenario_path: str, period: int = 1, marker: str | None = None) -> str:
    """
    Resolve `scenario_path` to an absolute scenario directory containing
    `marker` (default: results/results_p{period}/ReserveMargin_w.csv).

    Accepts an absolute path, a path relative to GENX_DIR, or a path relative
    to the current working directory.

    Defaults to Period 1. The marker field either takes in a string or None
    """

    # Marker doubles as validation that the run produced the default
    # result file `ReserveMargin_w.csv`.
    # Also used in diurnal_generation.py but for the `power.csv` file
    if marker is None:
        marker = os.path.join("results", f"results_p{period}", "ReserveMargin_w.csv")

    # i.e. ~/my/path/case_A expands
    expanded = os.path.expanduser(scenario_path)

    # Starts the candidate list for absolute filepaths.
    # If the path starts with `/` -> use directly
    candidates = [expanded] if os.path.isabs(expanded) else [os.path.abspath(expanded)]

    # Accomodates non absolute file path. GenX may not be configured at all --
    # a relative path resolved against the cwd is still worth trying.
    if not os.path.isabs(expanded):
        try:
            from GenX.tool_logic.slurm import genx_dir

            candidates.insert(0, os.path.join(genx_dir(), expanded))
        except Exception:
            pass

    # `candidates` are the list of absolute paths 
    # Checks if the given file (ex: `ReserveMargin_w` or `power.csv` exists)
    from GenX.tool_logic.slurm import _contained

    for cand in candidates:
        if os.path.isfile(os.path.join(cand, marker)):
            return _contained(os.path.abspath(cand), "scenario_path")
    # Nothing matched. Return the best candidate so the caller's own
    # missing-file check can name it; contain it first, since it is still a
    # model-supplied path that downstream code will try to open.
    return _contained(os.path.abspath(candidates[0]), "scenario_path")


def compute_capacity_cost(
    scenario_path: str,
    period: int = 1,
    capres_regions: list[int] | None = None,
    zones: list[int] | None = None,
) -> dict:
    """
    Compute capacity cost ($/MW-day) for a given scenario and period.

    Zone membership and per-zone reserve margin are read from Capacity_reserve_margin.csv.

    Args:
        scenario_path: Scenario directory.
        period: Model period number.
        capres_regions: CapRes region numbers to include in the cost numerator.
            Default -> Every CapRes_* column in ReserveMargin_w.csv.
        zones: Zone numbers for the peak-demand denominator.
            Default -> Every Demand_MW_z* column in Demand_data.csv.
    """
    scenario = resolve_scenario(scenario_path, period)

    dem_path    = os.path.join(scenario, "inputs", f"inputs_p{period}", "TDR_results", "Demand_data.csv")
    resmar_path = os.path.join(scenario, "results", f"results_p{period}", "ReserveMargin_w.csv")
    capres_path = os.path.join(scenario, "inputs", f"inputs_p{period}", "policies", "Capacity_reserve_margin.csv")

    for path in (dem_path, resmar_path, capres_path):
        if not os.path.isfile(path):
            return {"success": False,
                    "message": f"Missing required file: {path}"}

    dem_in = pd.read_csv(dem_path)
    resmar = pd.read_csv(resmar_path)
    capres = pd.read_csv(capres_path).set_index("Network_zones")

    # Timestep weights
    hours_per_period = int(dem_in["Timesteps_per_Rep_Period"].dropna().iloc[0])
    weights          = dem_in["Sub_Weights"].dropna().values
    hourly_weights   = np.array([w / hours_per_period for w in weights for _ in range(hours_per_period)])

    available_regions = sorted(
        int(c.split("_")[1]) for c in resmar.columns if c.startswith("CapRes_")
    )
    if capres_regions is None:
        capres_regions = available_regions
    else:
        unknown = sorted(set(capres_regions) - set(available_regions))
        if unknown:
            return {"success": False,
                    "message": f"Invalid CapRes region(s) {unknown}. "
                               f"Available regions: {available_regions}"}

    total_cost = 0.0
    for capres_num in capres_regions:
        capres_col = f"CapRes_{capres_num}"
        if capres_col not in resmar.columns or capres_col not in capres.columns:
            continue
        members = capres[capres[capres_col] != 0][capres_col]
        if members.empty:
            continue
        # sum_z D[t,z] * (1 + RM_z) -> reserve margin bump
        regional_demand = sum(
            dem_in[f"Demand_MW_z{int(zlabel[1:])}"].values * (1.0 + rm_z)
            for zlabel, rm_z in members.items()
        )
        lambda_t    = resmar[capres_col].values
        total_cost += (lambda_t * regional_demand * hourly_weights).sum()

    available_zones = sorted(
        int(c.split("_z")[1]) for c in dem_in.columns if c.startswith("Demand_MW_z")
    )
    if zones is None:
        denom_zones = available_zones
    else:
        invalid = sorted(set(zones) - set(available_zones))
        if invalid:
            return {"success": False,
                    "message": f"Invalid zone(s) {invalid}. "
                               f"Available zones: {available_zones}"}
        denom_zones = sorted(zones)

    peak_demand = dem_in[[f"Demand_MW_z{z}" for z in denom_zones]].sum(axis=1).values.max()
    if peak_demand <= 0:
        return {"success": False,
                "message": f"Peak demand across zone(s) {denom_zones} is "
                           f"{peak_demand}; a capacity price cannot be "
                           f"computed against zero demand."}
    price_annual = total_cost / peak_demand
    price_day    = price_annual / 365

    return {
        "success":          True,
        "scenario":         os.path.basename(scenario),
        "scenario_path":    scenario,
        "period":           period,
        "capres_regions":   list(capres_regions),
        "zones":            denom_zones,
        "price_per_mw_day": round(float(price_day), 2),
        "price_per_mw_yr":  round(float(price_annual), 2),
        "peak_demand_mw":   round(float(peak_demand), 1),
    }