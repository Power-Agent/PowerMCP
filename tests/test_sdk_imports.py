"""Every server has to be able to import the MCP SDK it names.

mcp 2.0 removed ``mcp.server.fastmcp`` and moved the server class to
``mcp.server.mcpserver.MCPServer``. This project requires ``mcp>=2,<3``, so a
file still importing the old module cannot start at all — and no existing test
noticed, because the suite launches only the servers whose engine is installed.

The check reads each file's AST instead of importing it: a bridge server pulls
in the simulator it wraps, which is absent in most environments, so importing to
find out would skip the check exactly where it matters.
"""

from __future__ import annotations

import ast
import importlib
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

SERVER_DIRS = (
    "ANDES",
    "Egret",
    "GenX",
    "HOPE",
    "LTSpice",
    "OpenDSS",
    "PLEXOSDB",
    "PSCAD",
    "PSLF",
    "PSSE",
    "PowerFactory",
    "PowerWorld",
    "PyPSA",
    "pandapower",
    "surge",
)

def _sdk_imports(path: pathlib.Path) -> list[tuple[str, str]]:
    """(module, name) for every ``from mcp... import name`` in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "mcp" or node.module.startswith("mcp."):
                found.extend((node.module, alias.name) for alias in node.names)
    return found


def _server_files() -> list[pathlib.Path]:
    files = []
    for name in SERVER_DIRS:
        directory = REPO / name
        if not directory.is_dir():
            continue
        files.extend(
            p
            for p in sorted(directory.rglob("*.py"))
            if "tests" not in p.parts and "__pycache__" not in p.parts
        )
    return files


def _resolves(module: str, name: str) -> bool:
    try:
        return hasattr(importlib.import_module(module), name)
    except ImportError:
        return False


@pytest.mark.parametrize("path", _server_files(), ids=lambda p: str(p.relative_to(REPO)))
def test_the_sdk_a_server_imports_exists(path):
    broken = [
        f"{module}.{name}"
        for module, name in _sdk_imports(path)
        if not _resolves(module, name)
    ]
    rel = path.relative_to(REPO)
    assert not broken, f"{rel} imports {broken}, which mcp>=2 does not provide"
