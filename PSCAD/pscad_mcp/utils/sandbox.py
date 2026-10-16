"""PowerIO path containment plus PSCAD's directory creation helper.

The standalone ``pscad-mcp`` distribution depends on PowerIO directly, so it
must not import PowerMCP's package-level compatibility module.  Keep the
policy implementation in PowerIO and localize only the small PSCAD-specific
operation that creates a missing directory tree one checked component at a
time.
"""

from __future__ import annotations

from pathlib import Path

from powerio.mcp.sandbox import (
    PathNotAllowed,
    checked_path,
    checked_read_tree,
    decode_local_path,
)


def ensure_checked_directory(value: str, *, purpose: str = "directory") -> str:
    """Create ``value`` without bypassing PowerIO's configured path roots."""
    target = decode_local_path(value, purpose=purpose)
    missing: list[Path] = []
    current = target

    while not current.exists():
        parent = current.parent
        if parent == current:
            raise PathNotAllowed(
                f"`{purpose}` cannot be created because its filesystem anchor "
                f"does not exist: {current}"
            )
        missing.append(current)
        current = parent

    checked_path(str(current), purpose=purpose)
    if not current.is_dir():
        raise PathNotAllowed(f"`{purpose}` parent is not a directory: {current}")

    for item in reversed(missing):
        checked = Path(
            checked_path(str(item), purpose=purpose, for_write=True)
        )
        try:
            checked.mkdir()
        except FileExistsError:
            if not checked.is_dir():
                raise PathNotAllowed(
                    f"`{purpose}` component is not a directory: {checked}"
                )

    result = checked_path(str(target), purpose=purpose, for_write=True)
    if not Path(result).is_dir():
        raise PathNotAllowed(f"`{purpose}` is not a directory: {result}")
    return result


__all__ = [
    "PathNotAllowed",
    "checked_path",
    "checked_read_tree",
    "ensure_checked_directory",
]
