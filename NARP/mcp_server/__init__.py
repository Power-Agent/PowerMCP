"""Minimal local MCP server package for reliability-assessment.
Expose JobManager for local programmatic use.
"""
from .manager import JobManager

__all__ = ["JobManager"]
