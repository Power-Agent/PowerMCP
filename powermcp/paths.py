"""Writable locations and sys.path helpers.

Servers must not write next to their installed source (a wheel in site-packages
is typically read-only). Runtime artifacts go under ``~/.powermcp/`` instead, and
are created lazily — never at import time.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import config_dir as powermcp_home  # ~/.powermcp (honours POWERMCP_HOME)

__all__ = ["powermcp_home", "runs_dir", "tool_data_dir", "inject_sys_path"]


def runs_dir(tool: str, *, create: bool = True) -> Path:
    """Per-tool directory for run artifacts, e.g. ~/.powermcp/runs/andes."""
    d = powermcp_home() / "runs" / tool
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def tool_data_dir(tool: str, *, create: bool = True) -> Path:
    """Per-tool directory for user data/config copies, e.g. ~/.powermcp/powerfactory."""
    d = powermcp_home() / tool
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def inject_sys_path(*paths: str | None, prepend_env_path: bool = False) -> None:
    """Prepend vendor directories to ``sys.path`` (and optionally to ``PATH`` for
    Windows DLL discovery). Skips empty/None entries; idempotent on ``sys.path``."""
    for raw in paths:
        if not raw:
            continue
        p = str(Path(raw).expanduser())
        if p not in sys.path:
            sys.path.insert(0, p)
        if prepend_env_path:
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
