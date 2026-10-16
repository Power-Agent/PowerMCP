# Imports
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display on a cluster login node
import matplotlib.pyplot as plt

from GenX.tool_logic.palette import RESOURCE_COLORS

# Resource name mapping for proper capitalization
resource_labels = {
    "coal": "Coal",
    "natural_gas": "Natural Gas",
    "solar": "Solar",
    "wind": "Wind",
    "battery": "Battery",
    "hydropower": "Hydro",
    "hydro": "Hydro",
    "nuclear": "Nuclear",
    "biomass": "Biomass",
}

# Colors for capacity bar graph, keyed by resource_group (shared palette)
resource_colors = {
    group: RESOURCE_COLORS[label] for group, label in resource_labels.items()
}

# Plot titles for each capacity column
column_titles = {
    "StartCap": "Start Capacity",
    "RetCap": "Retired Capacity",
    "NewCap": "New Capacity",
    "EndCap": "End Capacity",
    "NetCap": "Net Capacity Change",
}

# Classify resources for plotting

def classify_resource(resource):
    r = str(resource).lower()

    # Ignore rows that should not be visualized as resource types
    if r == "total":
        return "ignore"
    
    # Ignoring distributed generation for now
    if "distributed_generation" in r or "distributed generation" in r:
        return "ignore"

    # Storage
    if "batt" in r:
        return "battery"

    # Hydro
    if "hydroelectric" in r or "hydro" in r:
        return "hydro"

    # Solar
    if "utilitypv" in r:
        return "solar"
    if "solar" in r or "photovoltaic" in r:
        return "solar"

    # Wind
    if "wind" in r:
        return "wind"

    # Biomass
    if "biomass" in r:
        return "biomass"

    # Nuclear
    if "nuclear" in r:
        return "nuclear"

    # Coal
    if "coal" in r:
        return "coal"

    # Natural gas bucket including petroleum
    if "natural_gas" in r or "naturalgas" in r:
        return "natural_gas"
    if "petroleum" in r or "oil" in r:
        return "natural_gas"

    # Catch all for debugging
    return "unclassified"

# Filter to a user-specified list of zone numbers
def filter_by_zones(df: pd.DataFrame, zones: list[int]) -> pd.DataFrame:
    available_zones = sorted(int(z) for z in df["Zone"].dropna().unique())
    invalid = sorted(set(int(z) for z in zones) - set(available_zones))
    if invalid:
        raise ValueError(
            f"Invalid zone(s) {invalid}. Available zones: {available_zones}"
        )
    return df[df["Zone"].isin(zones)].copy()

# Interface with the csv to group resources by broader category
# Takes in a str with a hint for the type (string or [|] Path object)
def load_capacity_csv(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    required_cols = {"Resource", "StartCap", "RetCap", "NewCap", "EndCap"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required column(s) in capacity CSV {csv_path}: "
            f"{sorted(missing)}. Found: {sorted(df.columns)}"
        )

    df["resource_group"] = df["Resource"].apply(classify_resource)

    for col in ["StartCap", "RetCap", "NewCap", "EndCap"]:
        df[col] = pd.to_numeric(df[col])
    
    # Encompasses retirements and new builds
    df["NetCap"] = df["EndCap"] - df["StartCap"]

    return df

# Detecting the existence of StartCap > 0 (brownfield)
def check_existing(df: pd.DataFrame) -> dict:
    active_df = df[df["resource_group"] != "ignore"].copy()

    start_cap_by_resource = (
        active_df
        .groupby("resource_group", as_index=False)["StartCap"]
        .sum()
    )

    total_start_cap = start_cap_by_resource["StartCap"].sum()
    is_brownfield = total_start_cap > 0

    return {
        "is_brownfield": bool(is_brownfield),
        "setting": "brownfield" if is_brownfield else "greenfield",
        "total_start_cap": float(total_start_cap),
        "start_cap_by_resource": start_cap_by_resource.to_dict(orient="records"),
        "message": (
            f"Brownfield case detected: existing StartCap totals {total_start_cap:,.0f} MW."
            if is_brownfield
            else "Greenfield case detected: all StartCap values are zero."
        ),
    }

def aggregate_capacity_by_resource(df: pd.DataFrame) -> pd.DataFrame:
    active_df = df[df["resource_group"] != "ignore"].copy()

    grouped = (
        active_df.groupby("resource_group")
        .agg({
            "StartCap": "sum",
            "RetCap": "sum",
            "NewCap": "sum",
            "EndCap": "sum",
            "NetCap": "sum"
        })
        .reset_index()
    )

    return grouped

# Plot capacity bar chart
def plot_capacity_bar(
    df: pd.DataFrame,
    capacity_column: str,
    output_path: str | Path,
    title: str | None = None
) -> dict:
    """
    Create a bar chart of capacity by resource type.

    Args:
        df: DataFrame with aggregated capacity by resource_group
        capacity_column: Column name to plot (e.g., "StartCap", "EndCap")
        output_path: Path to save the PNG file
        title: Optional custom title for the plot

    Returns:
        dict with success status and file path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Drop bars under 10 MW in magnitude (zero capacity or solver noise)
    plot_df = df[df[capacity_column].abs() >= 10].copy()

    # Fixed left-to-right bar order; unknown groups go last
    resource_order = ["coal", "natural_gas", "solar", "wind", "battery", "hydro", "nuclear", "biomass"]
    plot_df["_order"] = plot_df["resource_group"].apply(
        lambda rg: resource_order.index(rg) if rg in resource_order else len(resource_order)
    )
    plot_df = plot_df.sort_values("_order").drop(columns="_order")

    # Create figure
    _, ax = plt.subplots(figsize=(10, 6))

    # Get colors for each resource group
    colors = [resource_colors.get(rg, "#808080") for rg in plot_df["resource_group"]]

    # Create bar chart with bars touching (width=1.0)
    bars = ax.bar(
        range(len(plot_df)),
        plot_df[capacity_column],
        width=1.0,
        color=colors
    )

    # No box around the plot: keep only the x and y axis lines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Customize plot
    ax.set_xticks(range(len(plot_df)))
    ax.set_xticklabels(
        [resource_labels.get(rg, rg.replace("_", " ").title()) for rg in plot_df["resource_group"]]
    )
    ax.set_ylabel("Capacity (MW)", fontsize=12)

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    else:
        ax.set_title(column_titles.get(capacity_column, capacity_column), fontsize=14, fontweight="bold")

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        # Round to nearest integer
        value = int(round(height))

        # Position label above bar for positive values
        # And above x-axis for negative values
        y_position = max(height, 0)

        ax.annotate(
            f"{value:,}",
            (bar.get_x() + bar.get_width() / 2.0, y_position),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9
        )

    # Tight layout
    plt.tight_layout()

    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    return {
        "success": True,
        "message": f"Plot saved successfully: {capacity_column}",
        "file_path": str(output_path),
    }