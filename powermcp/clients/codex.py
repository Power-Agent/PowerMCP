"""Write/merge MCP server entries into the OpenAI Codex CLI config (TOML).

Codex reads stdio MCP servers from ``[mcp_servers.<name>]`` tables in
``~/.codex/config.toml`` (override dir via ``CODEX_HOME``). We edit the file with
``tomlkit`` to preserve the user's comments, formatting, and other tables, and
only touch our own ``powermcp_*`` tables (idempotent + prune). Server names use
underscores (TOML table-name safe).

Note: the Codex *Desktop* app on Windows has been reported to rewrite
config.toml and drop user MCP servers on startup (openai/codex#24718); the Codex
CLI is unaffected. Documented for users who run both.
"""

from __future__ import annotations

import os
from pathlib import Path

from ._common import MANAGED_PREFIX, is_managed, launch_command, server_key

NAME = "codex"
DISPLAY = "Codex CLI"


def config_path() -> Path:
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return home / "config.toml"


def _build_doc(existing_text: str | None, tools: list[str]):
    import tomlkit

    doc = tomlkit.parse(existing_text) if existing_text else tomlkit.document()
    servers = doc.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        doc["mcp_servers"] = servers

    desired = {server_key(t) for t in tools}
    for name in list(servers.keys()):
        if is_managed(name) and name not in desired:
            del servers[name]

    command, base = launch_command()
    for tool in tools:
        table = tomlkit.table()
        table["command"] = command
        table["args"] = base + [tool]
        servers[server_key(tool)] = table
    return doc


def write(tools: list[str], *, dry_run: bool = False) -> str | None:
    import tomlkit

    path = config_path()
    existing_text = path.read_text(encoding="utf-8") if path.exists() else None
    doc = _build_doc(existing_text, tools)
    blob = tomlkit.dumps(doc)
    if dry_run:
        print(f"# would write {path}\n{blob}\n")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(".toml.powermcp.bak")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(blob, encoding="utf-8")
    tmp.replace(path)
    return str(path)
