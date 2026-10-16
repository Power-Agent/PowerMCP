"""OpenDSS MCP server powered by py-dss-toolkit."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

_repo_root = str(_root.parent)
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from core.server import create_mcp
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

mcp = create_mcp()

if __name__ == "__main__":
    mcp.run(transport="stdio")
