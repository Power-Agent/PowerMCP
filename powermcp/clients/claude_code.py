"""Write/merge MCP server entries for Claude Code (user scope).

Claude Code stores user-scope MCP servers at the root ``mcpServers`` object of
``~/.claude.json`` (the same object the `claude mcp add --scope user` CLI edits).
We merge directly into that file: this preserves the user's ``projects`` block
and every other key, is idempotent, supports pruning and dry-run, and does not
require the `claude` binary to be on PATH. Entries include ``"type": "stdio"``
per Claude Code's schema.
"""

from __future__ import annotations

from pathlib import Path

from ._common import write_json_config

NAME = "claude-code"
DISPLAY = "Claude Code"


def config_path() -> Path:
    return Path.home() / ".claude.json"


def write(tools: list[str], *, dry_run: bool = False) -> str | None:
    return write_json_config(config_path(), tools, include_type=True, dry_run=dry_run)
