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
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

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


@contextmanager
def _config_lock(*, timeout: float = 10.0, poll_interval: float = 0.05) -> Iterator[None]:
    """Serialize config mutations across processes using an exclusive lock file.

    The lock file remains in place intentionally. Unlinking it during release
    can let another process lock a different inode while a waiter still holds
    the old one. OS locks are released automatically when a process exits.
    """
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / "config.toml.lock"
    handle = lock_path.open("a+b")
    deadline = time.monotonic() + timeout
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt

            # Ensure the byte range exists before attempting to lock it.
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
        else:
            import fcntl

        while not acquired:
            try:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise ConfigError(
                        f"Timed out waiting for the configuration lock: {lock_path}"
                    )
                time.sleep(poll_interval)
        yield
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def load() -> dict[str, Any]:
    """Read the whole config. Returns ``{}`` if the file does not exist."""
    path = config_path()
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration root must be a TOML table: {path}")
    return data


def save(data: dict[str, Any]) -> None:
    """Atomically persist a config snapshot using a unique same-directory file.

    Callers performing a read-modify-write must hold ``_config_lock()`` across
    the complete sequence. Standalone snapshots are still atomically replaced.
    """
    if not isinstance(data, dict):
        raise TypeError("configuration data must be a dictionary")
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = config_path()
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(directory)
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            tomli_w.dump(data, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        if os.name != "nt":
            try:
                dir_fd = os.open(directory, os.O_RDONLY)
            except OSError:
                dir_fd = None
            if dir_fd is not None:
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def get(tool: str, key: str, default: Any = None) -> Any:
    """Low-level getter for a single ``[tool].key`` value."""
    return load().get(tool, {}).get(key, default)


def set_value(tool: str, key: str, value: Any) -> None:
    """Set a single ``[tool].key`` value and persist the file."""
    with _config_lock():
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
        from .registry import legacy_default

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
