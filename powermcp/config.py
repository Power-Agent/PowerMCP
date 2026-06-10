"""Central PowerMCP configuration at ``~/.powermcp/config.toml``.

This replaces the per-server hardcoded software paths. Vendor servers call
:func:`get_path` (before importing their vendor module) to learn where the local
software lives; the resolution order is:

1. environment variable ``POWERMCP_<TOOL>_<KEY>`` (handy for CI / overrides),
2. ``~/.powermcp/config.toml`` ``[tool].key``,
3. the historical hardcoded default declared in the registry (last resort),
4. otherwise raise :class:`ConfigError` with an actionable message.

The config dir can be relocated for tests via the ``POWERMCP_HOME`` env var.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


class ConfigError(RuntimeError):
    """Raised with a clear, user-facing message when a required path is missing."""


def config_dir() -> Path:
    """The ~/.powermcp directory (override with the POWERMCP_HOME env var)."""
    return Path(os.environ.get("POWERMCP_HOME", Path.home() / ".powermcp"))


def config_path() -> Path:
    return config_dir() / "config.toml"


def load() -> dict[str, Any]:
    """Read the whole config. Returns ``{}`` if the file does not exist."""
    path = config_path()
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def save(data: dict[str, Any]) -> None:
    """Atomically write the whole config (creates ~/.powermcp/ as needed)."""
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = config_path()
    tmp = path.with_suffix(".toml.tmp")
    with tmp.open("wb") as fh:
        tomli_w.dump(data, fh)
    tmp.replace(path)  # atomic on the same filesystem


def get(tool: str, key: str, default: Any = None) -> Any:
    """Low-level getter for a single ``[tool].key`` value."""
    return load().get(tool, {}).get(key, default)


def set_value(tool: str, key: str, value: Any) -> None:
    """Set a single ``[tool].key`` value and persist the file."""
    data = load()
    data.setdefault(tool, {})[key] = str(value)
    save(data)


def _env_key(tool: str, key: str) -> str:
    return "POWERMCP_" + tool.upper().replace("-", "_") + "_" + key.upper().replace(".", "_")


def get_path(tool: str, key: str, *, must_exist: bool = True) -> str:
    """Resolve a captured software path for ``tool``/``key``.

    Raises :class:`ConfigError` (with an actionable message) when the value is
    unset or points at a path that no longer exists.
    """
    env_name = _env_key(tool, key)
    value = os.environ.get(env_name) or get(tool, key)
    source = "config"
    if not value:
        from .registry import legacy_default  # lazy import: avoids any import cycle

        value = legacy_default(tool, key)
        source = "legacy default"
    if not value:
        raise ConfigError(
            f"[{tool}] required path '{key}' is not configured.\n"
            f"  Set it with one of:\n"
            f"    powermcp install                       (interactive wizard)\n"
            f"    powermcp config set {tool}.{key} <path>\n"
            f"    set {env_name}=<path>                   (environment override)"
        )
    resolved = Path(value).expanduser()
    if must_exist and not resolved.exists():
        raise ConfigError(
            f"[{tool}] path '{key}' ({source}) does not exist:\n"
            f"    {resolved}\n"
            f"  Fix it with:  powermcp config set {tool}.{key} <correct-path>"
        )
    return str(resolved)


def show() -> str:
    """A printable view of the current config for ``powermcp config show``."""
    data = load()
    if not data:
        return f"(no config yet at {config_path()} — run `powermcp install`)"
    return f"# {config_path()}\n" + tomli_w.dumps(data)
