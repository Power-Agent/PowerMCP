"""Session flags for the OpenDSS MCP server."""

from typing import Optional

circuit_loaded: bool = False
solution_available: bool = False
last_compiled_dss_file: Optional[str] = None
