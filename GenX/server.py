# genx_agent MCP server.

'''
Cluster settings (the GenX.jl checkout, SLURM defaults, module names) are
resolved at call time from ~/.powermcp/config.toml or the environment; see
GenX/README.md. Nothing is read at import, so this server starts on a machine
that has never configured GenX; the tools that need a setting say so when
they are called.
'''

import logging
import sys
from pathlib import Path
from typing import Optional

# Make the repo root importable so `from GenX.tool_logic...` works when the
# MCP client launches this file directly (sys.path[0] is GenX/, not the root).
# The entry stays for the process lifetime: GenX carries no __init__.py, so its
# namespace __path__ is recomputed from sys.path on every attribute lookup and
# the lazy `from GenX.tool_logic.slurm import ...` calls inside tool_logic
# would fail without it.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from mcp.server.mcpserver import MCPServer as FastMCP

from powermcp.errors import run_tool, tool_error, tool_success
from powermcp.sandbox import (
    checked_path,
    ensure_checked_directory,
)

# Analytics tools
from GenX.tool_logic.plot_capacity import (
    resource_colors,
    column_titles,
    classify_resource,
    load_capacity_csv,
    filter_by_zones,
    check_existing,
    aggregate_capacity_by_resource,
    plot_capacity_bar,
)

from GenX.tool_logic.compute_capacity_cost import compute_capacity_cost as _compute_capacity_cost
from GenX.tool_logic.plot_avg_generation import plot_diurnal_generation as _plot_diurnal_generation

# SLURM submission. Reads no configuration at import; genx_dir() resolves
# when a tool is called, so this server starts on an unconfigured machine.
from GenX.tool_logic.slurm import preview_case as _preview_case, submit_case as _submit_case

logger = logging.getLogger(__name__)

mcp = FastMCP("genx_agent")


def _checked(path: str, purpose: str) -> str:
    """Contain a model-supplied path, per powermcp/sandbox.py.

    Case and scenario arguments are not checked here: they may be given
    relative to the configured GenX directory, so only their resolvers know
    the path that will actually be opened. Those call checked_path themselves
    once resolution is done.
    """
    return checked_path(path, purpose=purpose)


def _checked_output_dir(path: str, purpose: str) -> str:
    """Contain a model-supplied output directory, creating it if needed.

    `checked_path(..., for_write=True)` requires an existing parent, and these
    plot tools are routinely pointed at a directory that does not exist yet,
    so the directory is walked into being one checked component at a time.
    """
    return ensure_checked_directory(path, purpose=purpose)


def _checked_output_file(path: str, purpose: str) -> str:
    """Contain a model-supplied output file, creating its directory if needed."""
    parent = Path(path).expanduser().parent
    _checked_output_dir(str(parent), purpose=f"{purpose} directory")
    return checked_path(path, purpose=purpose, for_write=True)


@mcp.tool()
def check_capacity_setting(csv_path: str) -> dict:
    """Detect whether a GenX capacity.csv is a brownfield or greenfield case."""
    def run() -> dict:
        df = load_capacity_csv(_checked(csv_path, "csv_path"))
        # check_existing: whether StartCap > 0 (brownfield) or all StartCap = 0 (greenfield)
        return tool_success(**check_existing(df))

    return run_tool(run, logger=logger)


@mcp.tool()
def summarize_capacity(csv_path: str, zones: list[int] | None = None) -> dict:
    """
    Aggregate StartCap, RetCap, NewCap, EndCap, and NetCap by resource type.

    Args:
        csv_path: Path to the capacity.csv file
        zones: Optional list of zone numbers (e.g., [2, 5, 7, 9]) to filter to
        before aggregating. Omit to aggregate over all zones.
    """
    def run() -> dict:
        df = load_capacity_csv(_checked(csv_path, "csv_path"))
        if zones:
            df = filter_by_zones(df, zones)
        # aggregate_capacity_by_resource returns a DataFrame; this is a
        # `-> dict` MCP tool, so it has to be serializable.
        aggregated = aggregate_capacity_by_resource(df)
        return tool_success(
            zones=zones,
            by_resource=aggregated.to_dict(orient="records"),
        )

    return run_tool(run, logger=logger)


@mcp.tool()
def plot_capacity(
    csv_path: str,
    output_dir: str,
    plot_type: str,
    scenario_name: str,
    period: str,
    zones: list[int] | None = None
) -> dict:
    """
    Plot capacity data and save to PNG file.

    Before calling this tool, ask user:
    1. Whether they want to specify zones to aggregate over. If they don't
       have specific zones, tell them the default is all zones in the
       capacity.csv file.
    2. The scenario folder to plot and the period, which go in the plot title.
    """
    def run() -> dict:
        valid_types = ["StartCap", "RetCap", "NewCap", "EndCap", "NetCap"]
        if plot_type not in valid_types:
            return tool_error(
                f"Invalid plot_type '{plot_type}'. Must be one of: {valid_types}",
                file_path=None,
            )

        df = load_capacity_csv(_checked(csv_path, "csv_path"))
        if zones:
            df = filter_by_zones(df, zones)
        aggregated = aggregate_capacity_by_resource(df)

        setting_info = check_existing(df)
        is_brownfield = setting_info["is_brownfield"]

        column = plot_type
        message_suffix = ""
        if not is_brownfield:
            if column in ["StartCap", "RetCap"]:
                return tool_error(
                    "In this case all StartCap = 0, so NewCap = EndCap = NetCap.",
                    file_path=None,
                    setting="greenfield",
                )
            if column == "NetCap":
                column = "EndCap"
                message_suffix = " Note that NewCap = EndCap = NetCap in this case"

        out_dir = _checked_output_dir(output_dir, "output_dir")
        output_path = Path(out_dir) / f"{column}.png"
        title = f"{column_titles[column]} {scenario_name} Period {period}"

        result = plot_capacity_bar(
            df=aggregated,
            capacity_column=column,
            output_path=output_path,
            title=title,
        )

        if result["status"] == "success":
            result["message"] += message_suffix
            result["setting"] = "brownfield" if is_brownfield else "greenfield"

        return result

    return run_tool(run, logger=logger)


@mcp.tool()
def preview_genx_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Generate the SLURM submission script for a GenX case.
    """
    return run_tool(
        lambda: _preview_case(case_dir, time_hours, mem_gb, cpus, case_name),
        logger=logger,
    )


@mcp.tool()
def submit_genx_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Submit a GenX case to SLURM via sbatch.

    Resolves the case from the given directory path and submits the job. Returns
    the SLURM job ID and the resource values used. Have the user submit walltime
    and memory requirements (#  cores and memory in gb).

    If the user has not stated this, ask before calling this tool.
    """
    return run_tool(
        lambda: _submit_case(case_dir, time_hours, mem_gb, cpus, case_name),
        logger=logger,
    )


@mcp.tool()
def compute_capacity_cost(
    scenario_path: str,
    period: int = 1,
    capres_regions: Optional[list[int]] = None,
    zones: Optional[list[int]] = None,
) -> dict:
    """
    Compute the capacity cost ($/MW-day and $/MW-yr) for a completed GenX
    scenario period, from the binding capacity reserve margin duals
    (ReserveMargin_w.csv).

    By default the cost is aggregated over every CapRes region and the peak
    demand over every zone in the case. Before calling, ask the user whether
    they want the computation over all zones or a specific subset; if they
    name a subset, pass it via capres_regions / zones.

    Args:
        scenario_path: Scenario directory (absolute, or relative to the
            configured GenX directory or the current working directory).
        period: Model period number. If the user hasn't specified a period,
            ask which one they want rather than assuming period 1.
        capres_regions: CapRes region numbers to include in the cost numerator
            (default: all regions in ReserveMargin_w.csv).
        zones: Zone numbers for the peak-demand denominator
            (default: all zones in Demand_data.csv).
    """
    return run_tool(
        lambda: _compute_capacity_cost(scenario_path, period, capres_regions, zones),
        logger=logger,
    )


@mcp.tool()
def plot_diurnal_generation(
    case_dir: str,
    output_path: str,
    period: int,
    zones: str,
    labels: str,
    compare_case_dir: Optional[str] = None,
    diff: bool = False,
) -> dict:
    """
    Plot the time-weighted average-day generation profile as a stacked area
    chart: MW of generation per resource type on the y-axis, hour of day
    (0-23) on the x-axis. Saves a PNG to output_path.

    Optionally compare two scenarios: pass compare_case_dir to plot both
    side by side, and set diff=True to instead plot the difference
    (Case 1 - Case 2) as a line chart.

    Args:
        case_dir: Case directory (absolute, or relative to the configured
            GenX directory or cwd).
        output_path: Path of the PNG file to write.
        period: Model period number. If the user hasn't specified a period,
            ask which one they want rather than assuming.
        zones: "all", or comma-separated zone numbers (e.g. "1,5,12"). If the
            user hasn't said which zones, ask whether to plot all zones or a
            specific subset.
        labels: Comma-separated plot label(s), e.g. "Base" or "Base, No CCS".
        compare_case_dir: Optional second case for pairwise comparison.
        diff: Plot Case 1 - Case 2 difference (requires compare_case_dir).
    """
    return run_tool(
        lambda: _plot_diurnal_generation(
            case_dir,
            _checked_output_file(output_path, "output_path"),
            period,
            zones,
            labels,
            compare_case_dir,
            diff,
        ),
        logger=logger,
    )

if __name__ == "__main__":
    mcp.run()