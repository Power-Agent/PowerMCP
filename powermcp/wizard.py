"""Interactive install wizard for `powermcp install`.

Flow: select tools (pandapower + PyPSA pre-checked) → capture local software
paths for closed-source tools → pip-install the chosen extras → write the
selected MCP client configs. Windows-only tools are hidden off Windows, and
surge is hidden on Python versions it doesn't support.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from . import config as cfg
from .clients import CLIENT_NAMES, configure
from .registry import CORE, TOOLS, Tool

console = Console()

DEFAULT_CLIENTS = ",".join(CLIENT_NAMES)


def _tty() -> bool:
    """True only when we can actually run interactive prompts."""
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except Exception:
        return False


def _surge_supported() -> bool:
    return (3, 12) <= sys.version_info[:2] < (3, 15)


def _platform_ok(tool: Tool) -> bool:
    if tool.windows_only and sys.platform != "win32":
        return False
    if tool.name == "surge" and not _surge_supported():
        return False
    return True


def selectable_tools() -> list[Tool]:
    return [t for t in TOOLS.values() if _platform_ok(t)]


def _parse_clients(clients: str) -> list[str]:
    return [c.strip() for c in clients.split(",") if c.strip() and c.strip().lower() != "none"]


def _is_installed_or_configured(t: Tool) -> bool:
    """Whether the tool is already set up on this machine.

    Tools that need a local software path (PSS/E, PSLF, PowerFactory, LTSpice,
    HOPE) count as set up only when those required paths are configured — not
    merely because some Python dep is importable (e.g. PyYAML being present must
    not make HOPE look ready). Tools with no required path count as set up when
    their dependency is importable.
    """
    required = [ck for ck in t.config_keys if ck.required]
    if required:
        return all(cfg.get(t.name, ck.key) for ck in required)
    from .runner import probe_installed

    return bool(t.probe) and probe_installed(t.probe)


def _existing_managed_tools(client_names: list[str]) -> set[str]:
    """Tool ids already registered as powermcp_* servers in the targeted clients,
    so re-running the wizard preserves them instead of pruning them."""
    from .clients import WRITERS
    from .clients._common import MANAGED_PREFIX

    found: set[str] = set()
    for name in client_names:
        writer = WRITERS.get(name)
        if writer is None:
            continue
        try:
            path = writer.config_path()
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        keys: list[str] = []
        try:
            if name == "codex":
                try:
                    import tomllib
                except ModuleNotFoundError:  # py3.10
                    import tomli as tomllib  # type: ignore
                keys = list((tomllib.loads(text).get("mcp_servers") or {}).keys())
            else:
                import json

                keys = list((json.loads(text or "{}").get("mcpServers") or {}).keys())
        except Exception:
            keys = []
        for key in keys:
            if key.startswith(MANAGED_PREFIX):
                found.add(key[len(MANAGED_PREFIX):])
    return found


def _preselected_names(client_names: list[str]) -> set[str]:
    """Tools to pre-check in the picker: core, already-configured-in-a-client, or
    already installed/configured on this machine."""
    existing = _existing_managed_tools(client_names)
    return {
        t.name
        for t in selectable_tools()
        if t.name in CORE or t.name in existing or _is_installed_or_configured(t)
    }


def run_wizard(
    *,
    yes: bool,
    tools: str | None = None,
    select_all: bool = False,
    clients: str = DEFAULT_CLIENTS,
    dry_run: bool = False,
) -> None:
    client_names = _parse_clients(clients)
    selected = _resolve_selection(yes=yes, tools=tools, select_all=select_all, client_names=client_names)
    if not selected:
        console.print("[yellow]No tools selected — nothing to do.[/]")
        return
    console.print("[bold]Selected:[/] " + ", ".join(t.name for t in selected))
    if not yes and not dry_run:  # --dry-run writes nothing, including config.toml
        _capture_paths(selected)
    _pip_install(selected, assume_yes=yes, dry_run=dry_run)
    _write_clients(selected, client_names, dry_run)
    console.print(f"\n[green]Done.[/] PowerMCP config: {cfg.config_path()}")


def _resolve_selection(
    *, yes: bool, tools: str | None, select_all: bool, client_names: list[str]
) -> list[Tool]:
    """Decide which tools to set up. The core tools are always included.

    Precedence: explicit ``--tools`` list (or ``all``) > ``--all`` flag >
    ``--yes`` (core only) > the interactive checkbox.
    """
    available = {t.name: t for t in selectable_tools()}

    if tools:
        requested = [s.strip().lower() for s in tools.split(",") if s.strip()]
        if "all" in requested:
            chosen = list(available)
        else:
            chosen, unknown, unavailable = [], [], []
            for name in requested:
                if name in available:
                    chosen.append(name)
                elif name in TOOLS:  # exists but not usable on this platform/Python
                    unavailable.append(name)
                else:
                    unknown.append(name)
            if unknown:
                console.print(
                    f"[red]Unknown tool id(s) ignored:[/] {', '.join(unknown)} "
                    f"(run `powermcp list` for valid ids)"
                )
            if unavailable:
                console.print(
                    f"[yellow]Not available on this platform/Python, skipped:[/] {', '.join(unavailable)}"
                )
        names = sorted(set(chosen) | set(CORE))
        return [TOOLS[n] for n in names]

    if select_all:
        names = sorted(set(available) | set(CORE))
        return [TOOLS[n] for n in names]

    if yes:
        return [TOOLS[n] for n in CORE]

    return _interactive_select(client_names)


def _interactive_select(client_names: list[str]) -> list[Tool]:
    if not _tty():
        console.print(
            "[yellow]No interactive terminal detected — defaulting to the core tools "
            "(pandapower, PyPSA). Re-run with `--tools <ids>` or `--all` to choose more.[/]"
        )
        return [TOOLS[n] for n in CORE]
    import questionary

    # Pre-check tools already set up (core, configured in a client, or installed),
    # so re-running preserves and updates your existing setup instead of resetting.
    preselect = _preselected_names(client_names)
    choices = [
        questionary.Choice(
            title=f"{t.display}  ({t.kind}{', windows-only' if t.windows_only else ''})",
            value=t.name,
            checked=(t.name in preselect),
        )
        for t in selectable_tools()
    ]
    try:
        picked = questionary.checkbox(
            "Select power-system tools to install:",
            choices=choices,
            instruction="(↑/↓ move · SPACE toggles a tool · ENTER confirms — pandapower & PyPSA are preselected)",
        ).ask()
    except Exception as exc:
        console.print(
            f"[yellow]Interactive picker unavailable ({exc}); defaulting to core tools. "
            f"Use `--tools <ids>` or `--all`.[/]"
        )
        return [TOOLS[n] for n in CORE]
    if picked is None:  # Ctrl-C
        console.print("[yellow]Selection cancelled.[/]")
        return []
    names = sorted(set(picked) | set(CORE))  # always include the core tools
    return [TOOLS[n] for n in names]


def _capture_paths(selected: list[Tool]) -> None:
    """Prompt for each closed-source tool's local software path(s). Accumulate
    everything and persist the config file in a single write at the end."""
    keyed = [t for t in selected if t.config_keys]
    if not keyed:
        return
    if not _tty():
        # No interactive terminal: tell the user how to set the required paths.
        for t in keyed:
            for ck in t.config_keys:
                if ck.required:
                    console.print(
                        f"[yellow]Set {t.name}.{ck.key} with:[/] "
                        f"powermcp config set {t.name}.{ck.key} <path>"
                    )
        return
    import questionary

    from .detect import detect

    data = cfg.load()
    changed = False
    for t in keyed:
        for ck in t.config_keys:
            existing = (data.get(t.name, {}) or {}).get(ck.key, "")
            # Prefill with the existing value, else an auto-detected install path,
            # so the user can usually just press Enter to accept.
            default = existing or detect(t.name, ck.key) or ""
            label = f"[{t.display}] {ck.prompt}"
            if default and not existing:
                console.print(f"[dim]  detected: {default}[/]")
            try:
                answer = questionary.path(label, default=default).ask()
            except Exception as exc:  # prompt backend unavailable
                console.print(
                    f"[yellow]Could not prompt for {t.name}.{ck.key} ({exc}); "
                    f"set it later with `powermcp config set {t.name}.{ck.key} <path>`.[/]"
                )
                answer = None
            if answer is None:  # cancelled / unavailable
                continue
            answer = answer.strip()
            if not answer:
                if ck.required:
                    console.print(
                        f"[yellow]{t.name}.{ck.key} left unset — {t.display} will report an "
                        f"actionable error until it is configured.[/]"
                    )
                continue
            path = Path(answer).expanduser()
            valid = (
                path.is_dir() if ck.validate == "dir"
                else path.is_file() if ck.validate == "file"
                else path.exists()
            )
            if not valid:
                try:
                    keep = questionary.confirm(
                        f"'{path}' does not exist as a {ck.validate}. Save anyway?", default=False
                    ).ask()
                except Exception:
                    keep = True  # can't prompt — keep the path the user explicitly typed
                if not keep:
                    continue
            data.setdefault(t.name, {})[ck.key] = str(path)
            changed = True
    if changed:
        cfg.save(data)


def _pip_install(selected: list[Tool], *, assume_yes: bool = False, dry_run: bool = False) -> None:
    extras = sorted({t.extra for t in selected if t.extra})
    spec = "powermcp" + (f"[{','.join(extras)}]" if extras else "")
    if dry_run:
        console.print(f"[cyan](dry-run)[/] would run: pip install {spec}")
        return
    if assume_yes:
        proceed = True
    elif not _tty():
        console.print(f"[yellow]Non-interactive — skipping dependency install. Run:[/] pip install {spec}")
        return
    else:
        import questionary

        try:
            proceed = bool(
                questionary.confirm(f"Install dependencies now?  pip install {spec}", default=True).ask()
            )
        except Exception:
            proceed = False
    if not proceed:
        console.print(f"[yellow]Skipped. Install later with:[/] pip install {spec}")
        return
    console.print(f"[cyan]Installing[/] {spec} ...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", spec], check=False)
    if result.returncode != 0:
        console.print(f"[red]pip install failed (exit {result.returncode}).[/] Install manually: pip install {spec}")


def _write_clients(selected: list[Tool], client_names: list[str], dry_run: bool) -> None:
    if not client_names:
        return
    for t in selected:
        for ck in t.config_keys:
            if not ck.required:
                continue
            try:
                cfg.get_path(t.name, ck.key)
            except cfg.ConfigError:
                console.print(
                    f"[yellow]Note:[/] {t.display} is configured for your MCP client(s) but "
                    f"{t.name}.{ck.key} is not set yet — set it with `powermcp config set {t.name}.{ck.key} <path>`."
                )
    tool_names = [t.name for t in selected]
    results = configure(client_names, tool_names, dry_run=dry_run)
    for client, path in results.items():
        if path:
            console.print(f"[green]Configured {client}:[/] {path}")
        elif not dry_run:
            console.print(f"[yellow]Skipped {client} (unknown client name).[/]")
