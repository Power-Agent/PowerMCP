"""
Compatibility wrapper that preserves the legacy ``NARP.mcp_server.server`` import path.

The canonical MCP tool definitions now live in :mod:`NARP.narp_mcp`; this module simply
re-exports them so existing entry points keep working.
"""

from ..narp_mcp import (
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
