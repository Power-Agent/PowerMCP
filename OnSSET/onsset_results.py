"""Read the outputs of finished OnSSET runs.

Works on the files the engine writes (``<name>_Run.json``, ``_Summaries.csv``, ``_Params.json``,
``_Results.csv``) and never recomputes model quantities: aggregates are plain sums of the
engine's settlement-level columns, in the engine's units.
"""

import json
import re
from pathlib import Path

import pandas as pd

import onsset_config as cfg
from onsset_jobs import result_path

TECH_LABELS = {1: "Grid_dens", 2: "Grid_ext", 3: "SA_PV", 5: "MG_PV_Hybrid", 6: "MG_Wind", 7: "MG_Hydro",
               99: "Non-electrified"}
UNITS = {"Population": "people", "NewConnections": "households", "Capacity": "MW", "Investment": "million USD",
         "Emissions": "ktCO2/year"}
# Settlement-level columns (per year suffix) and their units, as written by onsset.py.
SETTLEMENT_METRICS = {"Pop": "people", "ElecPop": "people", "NewConnections": "households",
                      "NewCapacity": "kW", "InvestmentCost": "USD", "AnnualEmissions": "tCO2/year",
                      "TotalEnergyPerCell": "kWh/year", "EnergyPerSettlement": "kWh/year"}
MAX_GROUPS = 200


def load_run(name):
    """The engine's result dict for a finished run, or ValueError explaining why there is none."""
    directory = cfg.run_dir(name)
    result = None
    path = result_path(directory, name)
    if path.exists():
        with open(path) as f:
            result = json.load(f)
    if result is None:
        if not directory.exists():
            raise ValueError(f"No run named '{name}' in {cfg.workspace()}.")
        raise ValueError(f"Run '{name}' has no result yet; check get_run_status.")
    if result.get("status") != "success":
        raise ValueError(f"Run '{name}' failed: {result.get('message')}")
    return result


def scenario_run(name):
    result = load_run(name)
    if "summary" not in result:
        raise ValueError(f"Run '{name}' is a {result.get('kind', 'non-scenario')} run, not a scenario run.")
    return result


def output_files(name):
    directory = cfg.run_dir(name)
    return [{"file": p.name, "path": str(p), "bytes": p.stat().st_size}
            for p in sorted(directory.iterdir()) if p.is_file()]


def _existing(path, what):
    if not Path(path).exists():
        raise ValueError(f"{what} is missing: {path}")
    return path


def summary(name):
    """Summary table, electrification rates and file inventory of a scenario run."""
    result = scenario_run(name)
    table = pd.read_csv(_existing(result["files"]["summary"], "Summary CSV"), index_col=0)
    return {"name": name,
            "years": result["years"],
            "start_year_stats": result["start_year_stats"],
            "electrification_rate": result["electrification_rate"],
            "summary_by_technology": json.loads(table.to_json(orient="index")),
            "units": UNITS,
            "notes": ["Rows are final technology codes: Grid_dens = densification of already grid-connected "
                      "settlements, Grid_ext = settlements newly reached by grid extension.",
                      "Capacity, investment and emissions are what is added in each period; emissions are "
                      "annual."],
            "timing_s": result.get("timing_s"),
            "files": output_files(name)}


def calibration_summary(name):
    result = load_run(name)
    if result.get("kind") != "calibration":
        raise ValueError(f"Run '{name}' is not a calibration run.")
    calibrated = _existing(result["files"]["calibrated_csv"], "Calibrated CSV")
    return {"name": name, "kind": "calibration", "calibration": result["calibration"],
            "calibrated_csv": str(Path(calibrated).resolve()),
            "next": "Use calibrated_csv as input_csv of start_scenario_run, with start_year "
                    f"{result['calibration']['start_year']}.",
            "timing_s": result.get("timing_s"), "files": output_files(name)}


def results_csv(name):
    return _existing(scenario_run(name)["files"]["results"], "Settlement results CSV")


def result_columns(name):
    """Columns of the settlement results grouped into per-year metrics and static attributes."""
    path = results_csv(name)
    columns = list(pd.read_csv(path, nrows=0).columns)
    per_year, static = {}, []
    for c in columns:
        m = re.fullmatch(r"(.+?)(\d{4})", c)
        if m and 1900 < int(m.group(2)) < 2200:
            per_year.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            static.append(c)
    n_rows = sum(1 for _ in open(path, "rb")) - 1
    return {"name": name, "path": path, "settlements": n_rows, "n_columns": len(columns),
            "per_year_metrics": {k: sorted(v) for k, v in per_year.items()},
            "static_columns": static,
            "metric_units": SETTLEMENT_METRICS,
            "final_elec_codes": TECH_LABELS}


def breakdown(name, group_by, year=None, max_groups=50):
    """Population, connections, capacity and investment per group and final technology."""
    result = scenario_run(name)
    year = int(year or result["years"][-1])
    if year not in result["years"]:
        raise ValueError(f"Year {year} is not a model year of '{name}' ({result['years']}).")
    path = results_csv(name)
    columns = set(pd.read_csv(path, nrows=0).columns)
    if group_by not in columns:
        candidates = sorted(c for c in columns if c in ("Admin_1", "Admin1", "Country", "IsUrban") or
                            c.startswith("Technology"))
        raise ValueError(f"Column '{group_by}' is not in the results. Candidates: {candidates}")
    metrics = {"Pop": "population", "NewConnections": "new_connections", "NewCapacity": "new_capacity_kw",
               "InvestmentCost": "investment_usd"}
    use = [group_by, f"FinalElecCode{year}"] + [f"{m}{year}" for m in metrics if f"{m}{year}" in columns]
    df = pd.read_csv(path, usecols=use)
    if df[group_by].nunique() > MAX_GROUPS:
        raise ValueError(f"'{group_by}' has {df[group_by].nunique()} distinct values; pick a column with at most "
                         f"{MAX_GROUPS} (e.g. an administrative region).")
    df["technology"] = df[f"FinalElecCode{year}"].map(TECH_LABELS).fillna("other")
    renamed = {f"{m}{year}": label for m, label in metrics.items()}
    df = df.rename(columns=renamed)
    values = [v for v in renamed.values() if v in df]
    totals = df.groupby(group_by)[values].sum()
    by_tech = df.pivot_table(index=group_by, columns="technology", values="population", aggfunc="sum",
                             fill_value=0)
    totals = totals.sort_values("population", ascending=False)
    groups = []
    for key, row in totals.head(max_groups).iterrows():
        entry = {"group": key.item() if hasattr(key, "item") else key,
                 **{k: float(v) for k, v in row.items()}}
        entry["population_by_technology"] = {t: float(v) for t, v in by_tech.loc[key].items() if v}
        groups.append(entry)
    return {"name": name, "year": year, "group_by": group_by, "n_groups": int(len(totals)),
            "groups_returned": len(groups), "groups": groups,
            "units": {"population": "people", "new_connections": "households", "new_capacity_kw": "kW",
                      "investment_usd": "USD"}}


def compare(names):
    """Side by side summary totals and parameter differences of two or more scenario runs."""
    if len(names) < 2:
        raise ValueError("Give at least two run names to compare.")
    runs = {n: scenario_run(n) for n in names}
    tables = {n: pd.read_csv(_existing(r["files"]["summary"], "Summary CSV"), index_col=0) for n, r in runs.items()}

    def final(table, metric, years):
        total = [c for c in table.columns if c.startswith(f"{metric}Total")]
        if total:
            return table[total[0]]
        return table[[c for c in table.columns if c.startswith(f"{metric}{years[-1]}")][0]]

    by_tech = {}
    for metric in ("Population", "NewConnections", "Capacity", "Investment", "Emissions"):
        by_tech[metric] = {n: {k: float(v) for k, v in final(tables[n], metric, runs[n]["years"]).items()}
                           for n in names}
    params = {}
    for n, r in runs.items():
        with open(_existing(r["files"]["params"], "Params JSON")) as f:
            params[n] = json.load(f)["params"]
    keys = sorted(set().union(*params.values()))
    differing = {k: {n: params[n].get(k) for n in names} for k in keys
                 if len({json.dumps(params[n].get(k), sort_keys=True) for n in names}) > 1}
    return {"runs": names,
            # JSON object keys are strings, so the years come back as "2050".
            "final_electrification_rate": {n: r["electrification_rate"][str(r["years"][-1])]
                                           for n, r in runs.items()},
            "years": {n: r["years"] for n, r in runs.items()},
            "by_technology": by_tech,
            "units": {**UNITS, "note": "Population is in the final year; the other metrics are summed over all "
                                       "periods (the Total column of each summary)."},
            "parameter_differences": differing}
