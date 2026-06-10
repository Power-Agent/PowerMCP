"""The ``powermcp`` command-line interface.

Commands
--------
- ``powermcp install``       interactive wizard: pick tools, capture vendor paths,
                             install extras, write MCP client config.
- ``powermcp run <tool>``    launch a server (used by the generated client config).
- ``powermcp config show``   print ~/.powermcp/config.toml.
- ``powermcp config set``    set a single ``tool.key`` path.
- ``powermcp doctor``        check deps + configured paths per tool.
- ``powermcp list``          list the known tools and their status.

Heavy modules (registry, runner, wizard, clients) are imported lazily inside the
command bodies so ``powermcp --help`` stays fast and works even before optional
pieces are present.
"""

from __future__ import annotations

import typer

from . import __version__

app = typer.Typer(
    name="powermcp",
    help="MCP servers for power-system software.",
    no_args_is_help=True,
    add_completion=False,
)
config_app = typer.Typer(help="Inspect or modify ~/.powermcp/config.toml.", no_args_is_help=True)
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"powermcp {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show the version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """PowerMCP — MCP servers for power-system software."""


# --------------------------------------------------------------------------- #
# install
# --------------------------------------------------------------------------- #
@app.command()
def install(
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive: install core only (pandapower + PyPSA)."),
    tools: str = typer.Option(
        None,
        "--tools",
        help="Comma-separated tool ids to set up (e.g. 'psse,andes'); use 'all' for everything "
        "available on this platform. Skips the interactive picker. Core tools are always included.",
    ),
    all_tools: bool = typer.Option(False, "--all", help="Set up every tool available on this platform."),
    clients: str = typer.Option(
        "claude-desktop,claude-code,codex",
        "--clients",
        help="Comma-separated MCP clients to configure (claude-desktop, claude-code, codex, none).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't write client config; print it."),
) -> None:
    """Installer: pick tools (interactively, or with --tools/--all), capture vendor
    software paths, install the chosen extras, and write the MCP client configuration."""
    from .wizard import run_wizard

    run_wizard(yes=yes, tools=tools, select_all=all_tools, clients=clients, dry_run=dry_run)


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #
@app.command()
def run(tool: str = typer.Argument(..., help="Tool id to launch, e.g. 'psse' or 'pandapower'.")) -> None:
    """Launch a server over stdio. Resolves the tool via the registry and runs
    the original server file unchanged, so standalone files keep working."""
    from .runner import launch

    launch(tool)


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #
@app.command(name="list")
def list_tools() -> None:
    """List the known tools, their kind, extra, and Windows-only flag."""
    from rich.console import Console
    from rich.table import Table

    from .registry import CORE, TOOLS

    table = Table(title="PowerMCP tools")
    table.add_column("tool")
    table.add_column("kind")
    table.add_column("extra")
    table.add_column("windows-only")
    table.add_column("default")
    for t in TOOLS.values():
        table.add_row(
            t.name,
            t.kind,
            t.extra or "(core)",
            "yes" if t.windows_only else "",
            "yes" if t.name in CORE else "",
        )
    Console().print(table)


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
@config_app.command("show")
def config_show() -> None:
    """Print the current ~/.powermcp/config.toml."""
    from . import config as cfg

    typer.echo(cfg.show())


@config_app.command("set")
def config_set(
    dotted: str = typer.Argument(..., help="A 'tool.key' pair, e.g. psse.bin"),
    value: str = typer.Argument(..., help="The path or value to store."),
) -> None:
    """Set a single config value, e.g. `powermcp config set ltspice.exe C:\\...\\LTspice.exe`."""
    from . import config as cfg

    if "." not in dotted:
        raise typer.BadParameter("expected the form tool.key (e.g. psse.bin)")
    tool, key = dotted.split(".", 1)
    cfg.set_value(tool, key, value)
    typer.echo(f"set [{tool}] {key} = {value}")


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #
@app.command()
def doctor(
    tool: str = typer.Argument(None, help="Optional: check a single tool instead of all."),
) -> None:
    """Verify that each selected tool's dependencies and configured paths are ready."""
    from .doctor import run_doctor

    run_doctor(tool)


def main() -> None:
    """Console-script entry point (``powermcp = powermcp.cli:main``)."""
    app()


if __name__ == "__main__":
    main()
