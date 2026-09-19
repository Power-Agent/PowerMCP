"""Shared pytest fixtures for the PowerMCP test suite."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

from powermcp.sandbox import ALLOWED_ROOTS_ENV, LEGACY_ROOT_ENVS

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def mcp_allowed_roots(tmp_path_factory):
    """Name the roots the suite writes to, for the whole session.

    powerio confines MCP paths to the directory the process started in when no
    root variable names one, so a test writing under pytest's temporary tree is
    refused unless that tree is named. Roots are resolved through ``realpath``
    because the policy compares real targets, and ``/tmp`` is a symlink on
    macOS while ``%TEMP%`` can carry a short name on Windows. A test that sets
    its own roots overrides this with ``monkeypatch``.
    """
    roots = [
        str(REPO_ROOT),
        os.path.realpath(tmp_path_factory.getbasetemp()),
        os.path.realpath(tempfile.gettempdir()),
    ]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(ALLOWED_ROOTS_ENV, os.pathsep.join(dict.fromkeys(roots)))
        for name in LEGACY_ROOT_ENVS:
            patch.delenv(name, raising=False)
        yield


@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    """Point ~/.powermcp at a throwaway dir and clear any POWERMCP_* env vars so
    config tests never read or write the developer's real configuration."""
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path))
    for var in list(__import__("os").environ):
        if var.startswith("POWERMCP_") and var != "POWERMCP_HOME":
            monkeypatch.delenv(var, raising=False)
    return tmp_path


@pytest.fixture()
def andes_mcp(tmp_path, monkeypatch):
    """Import andes_mcp from the registry-resolved server dir, skipping if
    andes is not installed.

    Shared by test_powerio_server.py (the powerio/pandapower bridge tools)
    and test_andes_server.py (the ANDES engine tools themselves).

    ``run_power_flow`` and friends name their run directory after the case
    stem, so two tests on the same case share one directory. Pointing
    POWERMCP_HOME at a per-test tmp_path keeps each test's artifacts to
    itself and keeps the suite out of the developer's real ~/.powermcp.
    """
    pytest.importorskip("andes")
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path / "powermcp-home"))
    from powermcp.registry import TOOLS

    andes_dir = str(TOOLS["andes"].resolve_server_dir())
    if andes_dir not in sys.path:
        sys.path.insert(0, andes_dir)
    import andes_mcp as _andes_mcp

    return _andes_mcp
