"""Pluggable MCP client-config writers.

Each writer module exposes ``NAME``, ``DISPLAY``, ``config_path()`` and
``write(tools, *, dry_run=False) -> str | None``. ``configure()`` dispatches to
the selected writers and returns a per-client result (the written path, or None
on dry-run / skip).
"""

from __future__ import annotations

from . import claude_code, claude_desktop, codex

WRITERS = {
    claude_desktop.NAME: claude_desktop,
    claude_code.NAME: claude_code,
    codex.NAME: codex,
}

CLIENT_NAMES = tuple(WRITERS)


def configure(client_names, tools, *, dry_run: bool = False) -> dict[str, str | None]:
    results: dict[str, str | None] = {}
    for name in client_names:
        writer = WRITERS.get(name)
        if writer is None:
            continue
        results[name] = writer.write(list(tools), dry_run=dry_run)
    return results
