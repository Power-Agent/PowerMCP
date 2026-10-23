#!/usr/bin/env python3
"""
Computes the average MW by hour-of-day across the modeled year, weighting each
model hour by its TDR time weight (results_pN/time_weights.csv).

Performs computation for each aggregated resource type.
"""
import argparse
import logging
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from GenX.tool_logic.palette import RESOURCE_COLORS
from GenX.tool_logic.resources import classify_resource

logger = logging.getLogger(__name__)

# Stack order, bottom -> top.
# DR is shed load (not generation) so it sits on top as a hatched band.
STACK_ORDER = ["Nuclear", "Coal", "Natural Gas", "Hydro", "Wind",
               "Solar", "Battery", "Other", "DR"]

COLORS = RESOURCE_COLORS # Referencing palette.py
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"


def classify(name):
    """Backward-compatible alias for the shared GenX resource classifier."""
    return classify_resource(name)


def zone_set(spec):
    # Converts a user's zone request into a set for the MCP tool to use
    # i.e. what comes in as "[1, 3, 5]" gets transformed to {1, 3, 5}
    if spec == "all":
        return None
    return {int(z) for z in spec.split(",")}


def diurnal_by_tech(case_dir, period, zones="all", verbose=False):
    # Returns a 24 x tech-group DataFrame of weight-averaged MW by hour of day
    res_dir = os.path.join(case_dir, "results", f"results_p{period}")
    power = pd.read_csv(os.path.join(res_dir, "power.csv"), index_col=0)
    weights = pd.read_csv(os.path.join(res_dir, "time_weights.csv"))["Weight"].to_numpy()
    if not np.isfinite(weights).all():
        raise ValueError(f"{case_dir}: time weights must all be finite")
    if (weights < 0).any():
        raise ValueError(f"{case_dir}: time weights must be non-negative")

    power = power.drop(columns=["Total"], errors="ignore")
    res_zone = power.loc["Zone"].astype(float).astype(int)
    data = power.drop(index=["Zone", "AnnualSum"]).astype(float)
    T = len(data)
    if T != len(weights):
        raise ValueError(f"{case_dir}: {T} timesteps but {len(weights)} weights")
    if T % 24:
        raise ValueError(f"{case_dir}: {T} timesteps is not a whole number of days")

    zf = zone_set(zones)
    if zf is not None:
        available = {int(z) for z in res_zone.unique()}
        # Check if the input zone number is part of the GenX case scenario
        invalid = sorted(zf - available)
        if invalid:
            raise ValueError(
                f"Invalid zone(s) {invalid}. Available zones: {sorted(available)}"
            )
        keep = res_zone[res_zone.isin(zf)].index
        data = data[keep]

    groups = {}
    for col in data.columns:
        groups.setdefault(classify(col), []).append(col)
    if verbose:
        for g in STACK_ORDER:
            if g in groups:
                logger.info("  %-8s <- %d resources", g, len(groups[g]))
        if "Other" in groups:
            techs = sorted({c.split("_", 1)[-1] for c in groups["Other"]})
            logger.info("  Other contains: %s", techs)

    hod = np.arange(T) % 24                      # t1 -> hour 0; 168 % 24 == 0 so
    wsum = np.bincount(hod, weights, minlength=24) # every rep week aligns
    uncovered_hours = np.flatnonzero(wsum <= 0).tolist()
    if uncovered_hours:
        raise ValueError(
            f"{case_dir}: no positive time-weight coverage for hour(s) "
            f"{uncovered_hours}; cannot compute weighted generation averages"
        )
    out = {}
    for g, cols in groups.items():
        x = data[cols].sum(axis=1).to_numpy()
        out[g] = np.bincount(hod, weights * x, minlength=24) / wsum

    # Stable snake_case keys are shared with the capacity classifier; translate
    # only at the presentation boundary so calculations remain consistent.
    label_by_key = {
        "natural_gas": "Natural Gas",
        "hydro": "Hydro",
        "nuclear": "Nuclear",
        "coal": "Coal",
        "wind": "Wind",
        "solar": "Solar",
        "battery": "Battery",
        "biomass": "Other",
        "other": "Other",
        "dr": "DR",
    }
    display_out = {}
    for key, values in out.items():
        label = label_by_key.get(key, "Other")
        if label in display_out:
            display_out[label] = display_out[label] + values
        else:
            display_out[label] = values

    df = pd.DataFrame(display_out, index=range(24))
    return df.reindex(columns=[g for g in STACK_ORDER if g in df.columns], fill_value=0.0)


def _style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xlim(0, 23)
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.margins(y=0)


def _stack(ax, df, unit_div):
    hours = df.index.to_numpy()
    base = np.zeros(len(df))
    for g in df.columns:
        top = base + df[g].to_numpy() / unit_div
        ax.fill_between(hours, base, top,
                        facecolor=COLORS[g], edgecolor="white", linewidth=0.7,
                        hatch="///" if g == "DR" else None)
        base = top
    return base  # total


def plot_comparison(orig_df, dr_df, labels, title, out_png):
    vmax = max(orig_df.sum(axis=1).max(), dr_df.sum(axis=1).max())
    unit_div, unit = (1000.0, "GW") if vmax > 10000 else (1.0, "MW")

    cols = [g for g in STACK_ORDER if g in set(orig_df.columns) | set(dr_df.columns)]
    orig_df = orig_df.reindex(columns=cols, fill_value=0.0)
    dr_df = dr_df.reindex(columns=cols, fill_value=0.0)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, facecolor="white")
    for ax, df, label in zip(axes, (orig_df, dr_df), labels):
        _stack(ax, df, unit_div)
        _style_axis(ax)
        ax.set_title(label, fontsize=11, color=INK, pad=8)
        ax.set_xlabel("Hour of day", fontsize=9.5, color=INK2)
    axes[0].set_ylabel(f"Average generation ({unit})", fontsize=9.5, color=INK2)

    handles = [Patch(facecolor=COLORS[g], edgecolor="white",
                     hatch="///" if g == "DR" else None, label=g)
               for g in reversed(cols)]
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.905, 0.5),
               frameon=False, fontsize=9, labelcolor=INK2)
    fig.suptitle(title, fontsize=12, color=INK, x=0.08, ha="left")
    fig.subplots_adjust(left=0.08, right=0.89, top=0.84, bottom=0.13, wspace=0.08)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    logger.info("wrote %s", out_png)


def plot_difference(orig_df, dr_df, labels, title, out_png):
    # Line plot of (dr - orig) by technology, per hour of day.
    # Reveals the formulation difference the near-identical stacks may hide

    cols = [g for g in STACK_ORDER if g in set(orig_df.columns) | set(dr_df.columns)]
    orig_df = orig_df.reindex(columns=cols, fill_value=0.0)
    dr_df = dr_df.reindex(columns=cols, fill_value=0.0)
    delta = dr_df - orig_df

    vmax = delta.abs().to_numpy().max()
    unit_div, unit = (1000.0, "GW") if vmax > 10000 else (1.0, "MW")
    hours = delta.index.to_numpy()

    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor="white")
    ax.axhline(0, color="#c3c2b7", linewidth=1)
    for g in cols:
        ax.plot(hours, delta[g].to_numpy() / unit_div,
                color=COLORS[g], linewidth=2, label=g)
    ax.plot(hours, delta.sum(axis=1).to_numpy() / unit_div,
            color=INK, linewidth=2.5, linestyle=(0, (4, 2)), label="Net total")
    _style_axis(ax)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color("#c3c2b7")
    ax.set_xlabel("Hour of day", fontsize=9.5, color=INK2)
    ax.set_ylabel(f"{labels[1]} − {labels[0]}  ({unit})", fontsize=9.5, color=INK2)
    ax.set_title(title, fontsize=12, color=INK, loc="left", pad=8)

    handles = [plt.Line2D([], [], color=COLORS[g], linewidth=2, label=g) for g in cols]
    handles.append(plt.Line2D([], [], color=INK, linewidth=2.5,
                              linestyle=(0, (4, 2)), label="Net total"))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5),
              frameon=False, fontsize=9, labelcolor=INK2)
    fig.subplots_adjust(left=0.1, right=0.82, top=0.9, bottom=0.12)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    logger.info("wrote %s", out_png)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--orig", required=True, help="original case folder")
    p.add_argument("--dr", required=True, help="DR / peak-shaving case folder")
    p.add_argument("--period", type=int, default=1)
    p.add_argument("--zones", default="all",
                   help="'all' (default) or comma-separated zone numbers")
    p.add_argument("--out", required=True, help="output PNG path")
    p.add_argument("--labels", default="Original,Demand response")
    p.add_argument("--diff", action="store_true",
                   help="plot (dr - orig) difference by tech instead of side-by-side stacks")
    args = p.parse_args()

    # Standalone CLI use: surface the logger output this module emits. When
    # imported by the MCP server instead, the server owns logging config and
    # nothing here touches stdout.
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("[orig] %s", args.orig)
    orig = diurnal_by_tech(args.orig, args.period, args.zones, verbose=True)
    logger.info("[dr]   %s", args.dr)
    dr = diurnal_by_tech(args.dr, args.period, args.zones, verbose=True)

    zone_lbl = "all zones" if args.zones == "all" else f"zones {args.zones}"
    kind = "difference" if args.diff else "generation by technology"
    title = f"Average day, {kind} — {zone_lbl}, p{args.period}"
    labels = args.labels.split(",")
    if args.diff:
        plot_difference(orig, dr, labels, title, args.out)
    else:
        plot_comparison(orig, dr, labels, title, args.out)


if __name__ == "__main__":
    main()