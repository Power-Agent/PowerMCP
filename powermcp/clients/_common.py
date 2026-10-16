"""Shared helpers for the MCP client-config writers.

All generated entries are namespaced with a ``powermcp_`` prefix so that merges
are idempotent and we only ever touch our own keys — a user's other MCP servers
are preserved untouched, and tools deselected on a re-run are pruned.

The launch command always uses the ABSOLUTE interpreter path
(``<python> -m powermcp run <tool>``) rather than a bare ``powermcp`` console
script, because GUI MCP hosts (Claude Desktop, etc.) do not inherit the user's
shell PATH and usually cannot find a venv's Scripts/ entry point.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MANAGED_PREFIX = "powermcp_"


def server_key(tool: str) -> str:
    """The mcpServers / mcp_servers key we manage for a tool."""
    return MANAGED_PREFIX + tool


def is_managed(key: str) -> bool:
    return key.startswith(MANAGED_PREFIX)


def launch_command() -> tuple[str, list[str]]:
    """(command, base_args) — absolute interpreter + `-m powermcp run`."""
    return sys.executable, ["-m", "powermcp", "run"]


def server_entry(tool: str, *, include_type: bool = False) -> dict:
    command, base = launch_command()
    entry: dict = {"command": command, "args": base + [tool]}
    if include_type:
        entry = {"type": "stdio", **entry}
    return entry


def merge_mcp_servers(existing: dict, tools: list[str], *, include_type: bool) -> dict:
    """Idempotently merge our entries into a parsed JSON config dict.

    - sets/overwrites only our ``powermcp_*`` keys,
    - prunes ``powermcp_*`` keys for tools no longer selected,
    - leaves every foreign server entry and every other top-level key untouched.
    """
    data = dict(existing)
    servers = dict(data.get("mcpServers") or {})
    desired = {server_key(t) for t in tools}
    for key in list(servers):
        if is_managed(key) and key not in desired:
            del servers[key]
    for tool in tools:
        servers[server_key(tool)] = server_entry(tool, include_type=include_type)
    data["mcpServers"] = servers
    return data


def write_json_config(path: Path, tools: list[str], *, include_type: bool, dry_run: bool) -> str | None:
    """Merge our entries into a JSON MCP-client config at ``path``.

    Returns the written path, or None in dry-run mode (after printing the result).
    Backs the file up once (``*.powermcp.bak``) and writes atomically.
    """
    existing: dict = {}
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        existing = json.loads(text) if text else {}
    merged = merge_mcp_servers(existing, tools, include_type=include_type)
    blob = json.dumps(merged, indent=2)
    if dry_run:
        print(f"# would write {path}\n{blob}\n")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".powermcp.bak")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(blob, encoding="utf-8")
    tmp.replace(path)
    return str(path)
