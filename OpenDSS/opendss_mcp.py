"""OpenDSS MCP server powered by py-dss-toolkit."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.server import create_mcp

mcp = create_mcp()

if __name__ == "__main__":
    mcp.run(transport="stdio")
