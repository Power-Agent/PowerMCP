"""Write/merge MCP server entries into Claude Desktop's config (JSON)."""

from __future__ import annotations

import sys
from pathlib import Path

from ._common import write_json_config

NAME = "claude-desktop"
DISPLAY = "Claude Desktop"


def config_path() -> Path:
    if sys.platform == "win32":
        import os

        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def write(tools: list[str], *, dry_run: bool = False) -> str | None:
    # Claude Desktop's classic schema is {command, args}; no "type" field needed.
    return write_json_config(config_path(), tools, include_type=False, dry_run=dry_run)
