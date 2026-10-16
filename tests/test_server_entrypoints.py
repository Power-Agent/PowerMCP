"""Every advertised server must import, register tools, and call MCP run."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from powermcp.registry import TOOLS

REPO = Path(__file__).resolve().parents[1]
SMOKE = Path(__file__).with_name("server_entry_smoke.py")
STANDALONE_SMOKE = Path(__file__).with_name("standalone_entry_smoke.py")


@pytest.mark.parametrize("tool_name", TOOLS)
def test_advertised_server_starts_without_vendor_engine(tool_name):
    result = subprocess.run(
        [sys.executable, str(SMOKE), tool_name],
        cwd=REPO,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


STANDALONE_SCRIPTS = {
    name: str(tool.resolve_entry_script().relative_to(REPO))
    for name, tool in TOOLS.items()
    if tool.run_kind == "script"
}


@pytest.mark.parametrize("tool_name,relative_script", STANDALONE_SCRIPTS.items())
def test_bundled_script_starts_from_an_uninstalled_clone(
    tool_name, relative_script, tmp_path
):
    result = subprocess.run(
        [sys.executable, str(STANDALONE_SMOKE), tool_name, relative_script],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_powerfactory_agent_imports_from_an_uninstalled_clone(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(STANDALONE_SMOKE),
            "powerfactory",
            "PowerFactory/Agent_DIgSILENT.py",
            "import-only",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
