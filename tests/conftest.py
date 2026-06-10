"""Shared pytest fixtures for the PowerMCP test suite."""

from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    """Point ~/.powermcp at a throwaway dir and clear any POWERMCP_* env vars so
    config tests never read or write the developer's real configuration."""
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path))
    for var in list(__import__("os").environ):
        if var.startswith("POWERMCP_") and var != "POWERMCP_HOME":
            monkeypatch.delenv(var, raising=False)
    return tmp_path
