"""Containment for paths that reach a server from the model.

An MCP tool argument is attacker-influenced input: whatever the model was
persuaded to ask for, the server does. A tool that takes a path and opens it
will read or write wherever the model points, so every such argument passes
through :func:`checked_path` first.

The policy itself lives in ``powerio.mcp.sandbox`` and this module only
re-exports it. powerio is a core dependency, the powerio MCP server already
applies that policy to its own ``path`` and ``out_path`` arguments, and
``powerio.mcp.sandbox`` imports nothing but the standard library, so there is
no second copy to keep in step. Operators configure containment once, with
``POWERIO_MCP_ALLOWED_ROOTS`` (an ``os.pathsep`` separated list of directories)
or one of the legacy single root spellings powerio still reads. With none set,
powerio confines paths to the directory the server process started in.

Resolution happens before the check, so neither a ``..`` segment nor a symlink
pointing out of a root gets through: it is the real target that is compared,
not the spelling.
"""

from __future__ import annotations

from pathlib import Path

from powerio.mcp.sandbox import (
    ALLOWED_ROOTS_ENV,
    LEGACY_ROOT_ENVS,
    PathNotAllowed,
    allowed_roots,
    check_allowed_path,
    check_allowed_read_tree,
    checked_path,
    checked_read_tree,
    decode_local_path,
    staged_directory_write,
    staged_file_write,
)


def ensure_checked_directory(value: str, *, purpose: str = "directory") -> str:
    """Create a directory tree without bypassing MCP path containment.

    ``checked_path(..., for_write=True)`` deliberately requires an existing
    parent.  Generated run directories often have several missing parents, so
    walk back to the first existing directory and create each component only
    after checking it.  The explicit anchor check matters on Windows: the
    parent of an unavailable drive or UNC anchor is the anchor itself.
    """
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
            # A cooperating process may have created it after the exists()
            # check.  Accept only a directory, never a file or dangling link.
            if not checked.is_dir():
                raise PathNotAllowed(
                    f"`{purpose}` component is not a directory: {checked}"
                )

    result = checked_path(str(target), purpose=purpose, for_write=True)
    if not Path(result).is_dir():
        raise PathNotAllowed(f"`{purpose}` is not a directory: {result}")
    return result


__all__ = [
    "ALLOWED_ROOTS_ENV",
    "LEGACY_ROOT_ENVS",
    "PathNotAllowed",
    "allowed_roots",
    "check_allowed_path",
    "check_allowed_read_tree",
    "checked_path",
    "checked_read_tree",
    "decode_local_path",
    "ensure_checked_directory",
    "staged_directory_write",
    "staged_file_write",
]
