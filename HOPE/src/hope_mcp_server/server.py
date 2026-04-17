from __future__ import annotations

import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .core import (
    hope_aggregation_audit,
    hope_cancel_job,
    hope_case_info,
    hope_close_dashboard,
    hope_debug_solver_environment,
    hope_debug_solver_environment_async,
    hope_compare_cases,
    hope_emission_compliance,
    hope_job_status,
    hope_nodal_prices,
    hope_open_dashboard,
    hope_output_summary,
    hope_read_output,
    hope_rep_day_audit,
    hope_run_erec,
    hope_run_holistic,
    hope_run_hope,
    hope_update_settings,
    hope_validate_case,
    hope_warmup,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_STDIO_PORT = 8000
DEFAULT_CHATGPT_PORT = 8001


def configured_host(default: str = DEFAULT_HOST) -> str:
    return os.environ.get("HOPE_MCP_HOST", default)


def configured_port(default: int) -> int:
    raw = os.environ.get("HOPE_MCP_PORT")
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def configured_public_hostname() -> str | None:
    raw = os.environ.get("HOPE_MCP_PUBLIC_HOSTNAME")
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def configured_transport_security(
    *,
    read_only: bool,
    host: str,
) -> TransportSecuritySettings | None:
    public_hostname = configured_public_hostname()
    if public_hostname:
        allowed_hosts = [
            public_hostname,
            f"{public_hostname}:443",
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
        ]
        allowed_origins = [
            f"https://{public_hostname}",
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
        ]
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )

    if read_only and host not in ("127.0.0.1", "localhost", "::1"):
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    return None


def create_mcp_server(
    *,
    read_only: bool = False,
    host: str | None = None,
    port: int | None = None,
) -> FastMCP:
    effective_host = host or configured_host()
    effective_port = port if port is not None else configured_port(
        DEFAULT_CHATGPT_PORT if read_only else DEFAULT_STDIO_PORT
    )
    server_name = "hope-mcp-readonly" if read_only else "hope-mcp"
    instructions = (
        "Read-only HOPE MCP server for ChatGPT remote access. "
        "Use any case directory name that exists under ModelCases "
        "(for example USA_64zone_GTEP_case or ISONE_PCM_250bus_case). "
        "This server exposes only read/fetch analysis tools and does not allow "
        "running cases, editing settings, or launching dashboards."
        if read_only
        else "HOPE MCP server for the local Julia repository. "
        "Use any case directory name that exists under ModelCases "
        "(for example USA_64zone_GTEP_case or ISONE_PCM_250bus_case). "
        "The legacy alias md_gtep_clean also still works. "
        "Typical workflow: hope_warmup -> hope_job_status (poll) -> hope_run_hope -> "
        "hope_job_status (poll) -> hope_output_summary / hope_read_output. "
        "If a Julia run needs to be stopped early, call hope_cancel_job with its job_id."
    )
    mcp = FastMCP(
        server_name,
        instructions=instructions,
        host=effective_host,
        port=effective_port,
        transport_security=configured_transport_security(
            read_only=read_only,
            host=effective_host,
        ),
    )
    register_read_tools(mcp)
    if not read_only:
        register_write_tools(mcp)
    return mcp


def register_read_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="hope_case_info",
        description=(
            "Return metadata and output inventory for a HOPE case: model mode, solver, "
            "boolean settings, and list of output CSV files. "
            "Pass any ModelCases directory name as case_id."
        ),
    )
    def hope_case_info_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_case_info(case_id)

    @mcp.tool(
        name="hope_output_summary",
        description=(
            "Summarize existing HOPE output CSVs for a case without running Julia. "
            "Returns total system cost, per-zone costs, new generation builds, and new storage builds."
        ),
    )
    def hope_output_summary_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_output_summary(case_id)

    @mcp.tool(
        name="hope_validate_case",
        description=(
            "Check a case's HOPE_model_settings.yml for contradictions and suspicious combinations "
            "(e.g., write_shadow_prices=1 without network_model > 0, or both endogenous and external "
            "rep-day enabled). Also checks that the solver settings file and DataCase folder exist. "
            "Returns a list of warnings and an is_valid flag."
        ),
    )
    def hope_validate_case_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_validate_case(case_id)

    @mcp.tool(
        name="hope_read_output",
        description=(
            "Read any CSV file from a case's output/ directory. "
            "Optionally filter rows by column values using the 'filters' dict "
            "(e.g., filters={'Zone': 'MD', 'Technology': 'SolarPV'}). "
            "Typical files: system_cost.csv, capacity.csv, es_capacity.csv, dispatch.csv, "
            "load_shed.csv, carbon_emissions.csv, rps_target.csv, nodal_prices.csv, "
            "storage_dispatch.csv, representative_period_metadata.csv, resource_aggregation_summary.csv. "
            "Use hope_case_info to list all available output files first."
        ),
    )
    def hope_read_output_tool(
        case_id: str = "md_gtep_clean",
        filename: str = "system_cost.csv",
        filters: dict[str, str] | None = None,
        max_rows: int = 200,
    ) -> dict[str, Any]:
        return hope_read_output(
            case_id=case_id,
            filename=filename,
            filters=filters,
            max_rows=max_rows,
        )

    @mcp.tool(
        name="hope_emission_compliance",
        description=(
            "Parse carbon emission and RPS (Renewable Portfolio Standard) compliance results "
            "from a completed HOPE run. Returns per-state compliance status, violation amounts, "
            "and penalty costs for both carbon cap and RPS policies. "
            "Requires carbon_policy > 0 or clean_energy_policy=1 to produce output files."
        ),
    )
    def hope_emission_compliance_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_emission_compliance(case_id)

    @mcp.tool(
        name="hope_nodal_prices",
        description=(
            "Read locational marginal prices (LMPs) from a completed nodal or zonal HOPE run. "
            "Filter by zone/bus name and/or hour range. "
            "Requires network_model > 0 and write_shadow_prices=1 in HOPE_model_settings.yml. "
            "Returns LMP values by bus/zone and hour."
        ),
    )
    def hope_nodal_prices_tool(
        case_id: str = "md_gtep_clean",
        zone_or_bus: str | None = None,
        hour_start: int | None = None,
        hour_end: int | None = None,
        max_rows: int = 500,
    ) -> dict[str, Any]:
        return hope_nodal_prices(
            case_id=case_id,
            zone_or_bus=zone_or_bus,
            hour_start=hour_start,
            hour_end=hour_end,
            max_rows=max_rows,
        )

    @mcp.tool(
        name="hope_compare_cases",
        description=(
            "Compare system cost, capacity builds (MW by technology), storage builds (MWh by technology), "
            "and total CO2 emissions across two or more HOPE cases. "
            "Returns side-by-side tables and cost/emissions diffs relative to the first (baseline) case. "
            "Example: hope_compare_cases(['MD_GTEP_clean_case', 'USA_64zone_GTEP_case'])."
        ),
    )
    def hope_compare_cases_tool(case_ids: list[str]) -> dict[str, Any]:
        return hope_compare_cases(case_ids)

    @mcp.tool(
        name="hope_rep_day_audit",
        description=(
            "Summarize representative-period clustering results from a completed HOPE run. "
            "Returns period assignments (day -> period), period weights, total representative hours, "
            "and the compression ratio compared to a full 8760-hour year. "
            "Only available when endogenous_rep_day=1 or external_rep_day=1."
        ),
    )
    def hope_rep_day_audit_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_rep_day_audit(case_id)

    @mcp.tool(
        name="hope_aggregation_audit",
        description=(
            "Summarize resource aggregation results from a completed HOPE run. "
            "Returns the raw->aggregated generator cluster mapping, reduction ratio "
            "(e.g., 120 generators -> 30 clusters = 4x reduction), and total capacity by cluster. "
            "Only available when resource_aggregation=1."
        ),
    )
    def hope_aggregation_audit_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_aggregation_audit(case_id)


def register_write_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="hope_warmup",
        description=(
            "Pre-compile the HOPE Julia environment in the background so subsequent hope_run_hope calls "
            "start fast. Returns a job_id immediately. Call hope_job_status to check progress. "
            "Run this once per Claude Desktop session before the first hope_run_hope."
        ),
    )
    def hope_warmup_tool() -> dict[str, Any]:
        return hope_warmup()

    @mcp.tool(
        name="hope_job_status",
        description=(
            "Poll the status of a background Julia job launched by hope_warmup, hope_run_hope, "
            "hope_run_holistic, or hope_run_erec. "
            "Returns status ('running' or 'done'), elapsed time, stdout tail, and on success the "
            "output summary. Call repeatedly until status is 'done'."
        ),
    )
    def hope_job_status_tool(job_id: str) -> dict[str, Any]:
        return hope_job_status(job_id)

    @mcp.tool(
        name="hope_cancel_job",
        description=(
            "Cancel a background Julia job launched by hope_warmup, hope_run_hope, "
            "hope_run_holistic, or hope_run_erec. "
            "Pass the job_id returned by the launch tool. "
            "Returns status='cancelled' when the subprocess is terminated successfully."
        ),
    )
    def hope_cancel_job_tool(job_id: str) -> dict[str, Any]:
        return hope_cancel_job(job_id)

    @mcp.tool(
        name="hope_debug_solver_environment",
        description=(
            "Run a short Julia probe in the same MCP-server environment used for HOPE jobs. "
            "Returns the active project, depot path, loaded HOPE source path, and the exact "
            "optimizer constructor JuMP sees for the selected solver. "
            "Use this when Claude appears to be running stale code or the wrong Julia environment."
        ),
    )
    def hope_debug_solver_environment_tool(
        case_id: str = "md_gtep_clean",
        solver: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> dict[str, Any]:
        return hope_debug_solver_environment(
            case_id=case_id,
            solver=solver,
            timeout_seconds=timeout_seconds,
        )

    @mcp.tool(
        name="hope_debug_solver_environment_async",
        description=(
            "Launch the HOPE Julia environment probe as a background job and return a job_id immediately. "
            "Use hope_job_status to inspect stdout, stderr, and parsed probe fields without Claude timing out."
        ),
    )
    def hope_debug_solver_environment_async_tool(
        case_id: str = "md_gtep_clean",
        solver: str | None = None,
    ) -> dict[str, Any]:
        return hope_debug_solver_environment_async(case_id=case_id, solver=solver)

    @mcp.tool(
        name="hope_run_hope",
        description=(
            "Launch a HOPE single-case run as a background job. Returns a job_id immediately. "
            "Poll with hope_job_status until done. Works for both GTEP and PCM model modes. "
            "Pass any ModelCases directory name as case_id."
        ),
    )
    def hope_run_hope_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
        return hope_run_hope(case_id)

    @mcp.tool(
        name="hope_update_settings",
        description=(
            "Patch fields in a case's HOPE_model_settings.yml. "
            "Pass a 'changes' dict mapping setting keys to new values "
            "(e.g., {'carbon_policy': 2, 'solver': 'highs', 'network_model': 1}). "
            "Validates values, backs up the original file, and returns applied/rejected changes plus warnings. "
            "Key options - model_mode: GTEP|PCM; solver: cbc|clp|highs|scip|gurobi|cplex; "
            "carbon_policy: 0|1|2; network_model: 0|1|2|3; unit_commitment: 0|1|2; "
            "clean_energy_policy: 0|1; planning_reserve_mode: 0|1|2; and any binary (0/1) setting."
        ),
    )
    def hope_update_settings_tool(
        case_id: str = "md_gtep_clean",
        changes: dict[str, Any] | None = None,
        backup: bool = True,
    ) -> dict[str, Any]:
        return hope_update_settings(case_id=case_id, changes=changes, backup=backup)

    @mcp.tool(
        name="hope_run_holistic",
        description=(
            "Run the two-stage GTEP->PCM holistic workflow as a background job. "
            "Stage 1 solves capacity expansion (GTEP) to determine optimal new builds and retirements. "
            "Stage 2 fixes the resulting fleet and runs a full PCM (production cost model) "
            "to validate operational feasibility and compute hourly dispatch + LMPs. "
            "Returns a job_id immediately. Poll with hope_job_status."
        ),
    )
    def hope_run_holistic_tool(
        gtep_case_id: str,
        pcm_case_id: str,
    ) -> dict[str, Any]:
        return hope_run_holistic(gtep_case_id=gtep_case_id, pcm_case_id=pcm_case_id)

    @mcp.tool(
        name="hope_run_erec",
        description=(
            "Run EREC (Equivalent Reliability Enhancement Capability) postprocessing on a completed HOPE run. "
            "EREC computes how much unserved energy each generation or storage resource avoids, "
            "quantifying each resource's reliability contribution. "
            "Requires save_postprocess_snapshot >= 1 in HOPE_model_settings.yml and a completed run. "
            "Optionally override voll_override ($/MWh Value of Lost Load) and delta_mw (marginal capacity step). "
            "Returns a job_id immediately. Poll with hope_job_status."
        ),
    )
    def hope_run_erec_tool(
        case_id: str = "md_gtep_clean",
        voll_override: float | None = None,
        delta_mw: float | None = None,
    ) -> dict[str, Any]:
        return hope_run_erec(
            case_id=case_id,
            voll_override=voll_override,
            delta_mw=delta_mw,
        )

    @mcp.tool(
        name="hope_open_dashboard",
        description=(
            "Launch the local HOPE Dash dashboard for a completed case run and return its URL. "
            "Automatically picks the GTEP dashboard (port 8051) for GTEP cases and the PCM dashboard "
            "(port 8050) for PCM cases. "
            "If a dashboard is already running on the target port, returns the existing URL immediately. "
            "After the browser URL opens, select the matching case from the dropdown in the UI. "
            "Requires Python with dash, plotly, pandas installed "
            "(set HOPE_PYTHON_BIN env var to point to that Python if needed). "
            "Optional 'port' overrides the default port."
        ),
    )
    def hope_open_dashboard_tool(
        case_id: str = "md_gtep_clean",
        port: int | None = None,
    ) -> dict[str, Any]:
        return hope_open_dashboard(case_id=case_id, port=port)

    @mcp.tool(
        name="hope_close_dashboard",
        description=(
            "Stop a running HOPE dashboard that was launched by hope_open_dashboard. "
            "If 'port' is given (8050 for PCM, 8051 for GTEP), stop only that dashboard. "
            "If omitted, stop all dashboards tracked by this session. "
            "Returns a list of stopped processes with their ports and exit codes. "
            "Only dashboards started in the current Claude Desktop session can be stopped this way."
        ),
    )
    def hope_close_dashboard_tool(port: int | None = None) -> dict[str, Any]:
        return hope_close_dashboard(port=port)


def main() -> None:
    create_mcp_server(read_only=False).run("stdio")


if __name__ == "__main__":
    main()
