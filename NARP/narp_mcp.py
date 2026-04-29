"""
PowerMCP integration layer for the NARP reliability assessment tools.

This module mirrors the style used by the other integrations (e.g. pandapower) by
exposing a `FastMCP` instance alongside decorated tool functions. The actual job
execution logic lives in :mod:`NARP.mcp_server.manager` and :mod:`NARP.mcp_server.worker`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from common.utils import PowerError, power_mcp_tool
from mcp.server.fastmcp import FastMCP

from .mcp_server.manager import JobManager

logger = logging.getLogger(__name__)
logger.info("Initializing NARP Reliability Assessment MCP tools")

# Public MCP server instance matching the repository convention.
mcp = FastMCP("NARP Reliability Assessment Server")

# Reuse a single job manager instance so that tooling retains job history.
_job_manager = JobManager(max_workers=1)

# Required input artefacts expected by the native NARP workflow.
_REQUIRED_INPUT_FILES = (
    "ZZMC.csv",
    "ZZUD.csv",
    "ZZLD.csv",
    "ZZTD.csv",
    "ZZTC.csv",
    "LEEI",
)


def _coerce_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a mutable params dictionary for downstream calls."""
    return dict(params) if params else {}


@power_mcp_tool(mcp)
def submit_simulation(test_dir: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Submit an asynchronous simulation job.

    Args:
        test_dir: Path to a directory containing the NARP input files.
        params: Optional runtime parameters to pass through to the worker.
    """
    payload = _coerce_params(params)
    logger.info("Submitting NARP simulation for %s", test_dir)
    try:
        return _job_manager.submit_simulation(test_dir, payload)
    except Exception as exc:
        logger.exception("Failed to submit NARP simulation from %s", test_dir)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def run_simulation_sync(test_dir: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run a simulation synchronously (blocking until completion).

    Returns the final job metadata – callers can inspect ``result`` and ``status`` fields.
    """
    payload = _coerce_params(params)
    logger.info("Running synchronous NARP simulation for %s", test_dir)
    try:
        result = _job_manager.run_simulation_sync(test_dir, payload)
        return {"result": result}
    except Exception as exc:
        logger.exception("Synchronous NARP simulation failed for %s", test_dir)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Return the status metadata for a previously submitted job."""
    try:
        job = _job_manager.get_job_status(job_id)
        return {"job": job}
    except KeyError:
        logger.warning("Requested status for unknown NARP job %s", job_id)
        return PowerError(status="error", message=f"Job not found: {job_id}")
    except Exception as exc:
        logger.exception("Failed to retrieve status for NARP job %s", job_id)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def get_job_result(job_id: str) -> Dict[str, Any]:
    """
    Retrieve the raw ``output_python.txt`` content for a job.

    The worker writes this file into the job directory after completion.
    """
    try:
        result = _job_manager.get_job_result(job_id)
        return {"result": result}
    except KeyError:
        logger.warning("Requested result for unknown NARP job %s", job_id)
        return PowerError(status="error", message=f"Job not found: {job_id}")
    except Exception as exc:
        logger.exception("Failed to retrieve result for NARP job %s", job_id)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def get_job_summary(job_id: str) -> Dict[str, Any]:
    """
    Return the parsed TABLE 12 / TABLE 13 summary extracted from ``output_python.txt``.

    Parsing is performed lazily using :func:`NARP.mcp_server.worker.parse_output`.
    """
    try:
        summary = _job_manager.get_job_summary(job_id)
        return summary
    except KeyError:
        logger.warning("Requested summary for unknown NARP job %s", job_id)
        return PowerError(status="error", message=f"Job not found: {job_id}")
    except Exception as exc:
        logger.exception("Failed to retrieve summary for NARP job %s", job_id)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def list_jobs(limit: int = 100) -> Dict[str, Any]:
    """List the most recent jobs tracked by the manager (sorted newest first)."""
    try:
        jobs = _job_manager.list_jobs()
        return {"jobs": jobs[:limit]}
    except Exception as exc:
        logger.exception("Failed to list NARP jobs")
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def cancel_job(job_id: str) -> Dict[str, Any]:
    """Attempt to cancel a running or pending job."""
    try:
        cancelled = _job_manager.cancel_job(job_id)
        return {"cancelled": bool(cancelled)}
    except Exception as exc:
        logger.exception("Failed to cancel NARP job %s", job_id)
        return PowerError(status="error", message=str(exc))


@power_mcp_tool(mcp)
def validate_input(test_dir: str) -> Dict[str, Any]:
    """
    Validate that the directory contains the files required by the NARP pipeline.
    """
    try:
        td = Path(test_dir)
        missing = [name for name in _REQUIRED_INPUT_FILES if not td.joinpath(name).exists()]
        if missing:
            return {"valid": False, "missing": missing}
        return {"valid": True}
    except Exception as exc:
        logger.exception("Failed to validate NARP input directory %s", test_dir)
        return PowerError(status="error", message=str(exc))


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
