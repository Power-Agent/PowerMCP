"""
NARP reliability assessment integration for PowerMCP.

Re-exports the MCP server instance and tool functions from :mod:`NARP.narp_mcp`
so callers can simply import ``NARP`` and access the registered tools.
"""

from .narp_mcp import (
    mcp,
    submit_simulation,
    run_simulation_sync,
    get_job_status,
    get_job_result,
    get_job_summary,
    list_jobs,
    cancel_job,
    validate_input,
)

__all__ = [
    "mcp",
    "submit_simulation",
    "run_simulation_sync",
    "get_job_status",
    "get_job_result",
    "get_job_summary",
    "list_jobs",
    "cancel_job",
    "validate_input",
]
