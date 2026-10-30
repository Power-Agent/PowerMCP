"""Paths, limits and path containment for the OnSSET MCP server.

Every setting is read from the environment at call time, so the server starts on a machine
where nothing is configured and the tools that need a setting say so when called.

    ONSSET_REPO             OnSSET checkout (notebooks, example data). Default: the checkout the
                            engine interpreter imports ``onsset`` from (editable install).
    ONSSET_PYTHON           Interpreter that runs the engine subprocesses. Default: this one.
    ONSSET_WORKSPACE        Directory that holds one folder per calibration/scenario run.
                            Default: ``runs/`` next to this file.
    ONSSET_ALLOWED_ROOTS    Extra directories (os.pathsep separated) the tools may read inputs
                            from. The repo and the workspace are always allowed.
    ONSSET_MAX_CONCURRENT_RUNS  Engine subprocesses allowed at once (default 1; a national
                            run holds several GB in memory).
"""

import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE_SCRIPT = HERE / "onsset_engine.py"
CALIBRATION_SCRIPT = HERE / "onsset_calibration.py"

RUN_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class ConfigError(RuntimeError):
    """A setting is missing or points somewhere unusable."""


class PathNotAllowed(ValueError):
    """A tool argument points outside the allowed directories."""


def engine_python():
    value = os.environ.get("ONSSET_PYTHON")
    if not value:
        return sys.executable
    if not Path(value).is_file():
        raise ConfigError(f"ONSSET_PYTHON does not point to a file: {value}")
    return value


def workspace():
    """The run workspace, created on first use."""
    path = Path(os.environ.get("ONSSET_WORKSPACE") or HERE / "runs").expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


@lru_cache(maxsize=4)
def _probe_onsset_location(python):
    """Directory holding the ``onsset`` package as seen by ``python`` (no import side effects)."""
    code = "import importlib.util as u, json; s = u.find_spec('onsset'); print(json.dumps(s and s.origin))"
    try:
        out = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=60,
                             stdin=subprocess.DEVNULL)
        origin = json.loads(out.stdout.strip() or "null")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return str(Path(origin).resolve().parent) if origin else None


def onsset_repo(required=True):
    """The OnSSET checkout, or None when it cannot be found and ``required`` is False."""
    value = os.environ.get("ONSSET_REPO")
    if value:
        path = Path(value).expanduser().resolve()
        if not path.is_dir():
            raise ConfigError(f"ONSSET_REPO is not a directory: {path}")
        return path
    package_dir = _probe_onsset_location(engine_python())
    if package_dir:
        # An editable install resolves to <repo>/onsset/__init__.py; a wheel to site-packages.
        repo = Path(package_dir).parent
        if (repo / "onsset" / "onsset.py").exists() and (repo / ".git").exists():
            return repo
    if required:
        raise ConfigError("OnSSET checkout not found. Set ONSSET_REPO to the OnSSET repository directory "
                          "(e.g. C:\\Users\\<you>\\Desktop\\onsset).")
    return None


def max_concurrent_runs():
    try:
        return max(1, int(os.environ.get("ONSSET_MAX_CONCURRENT_RUNS", "1")))
    except ValueError:
        raise ConfigError("ONSSET_MAX_CONCURRENT_RUNS must be an integer") from None


def allowed_roots():
    roots = [workspace()]
    repo = onsset_repo(required=False)
    if repo:
        roots.append(repo)
    for item in os.environ.get("ONSSET_ALLOWED_ROOTS", "").split(os.pathsep):
        if item.strip():
            roots.append(Path(item.strip()).expanduser().resolve())
    return list(dict.fromkeys(roots))


def _within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_input(value, purpose, kind="file"):
    """Resolve a model-supplied input path and check it is inside an allowed root.

    Relative paths are resolved against the OnSSET repo, then the workspace. Symlinks and
    ``..`` are resolved before the check, so the real target is what gets compared.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{purpose}: a path is required")
    raw = Path(value.strip().strip('"')).expanduser()
    if raw.is_absolute():
        path = raw.resolve()
    else:
        bases = [b for b in (onsset_repo(required=False), workspace()) if b]
        candidates = [(b / raw).resolve() for b in bases]
        path = next((c for c in candidates if c.exists()), candidates[0])
    roots = allowed_roots()
    if not any(_within(path, r) for r in roots):
        raise PathNotAllowed(f"{purpose}: {path} is outside the allowed directories "
                             f"({', '.join(map(str, roots))}). Add its folder to ONSSET_ALLOWED_ROOTS.")
    if kind == "file" and not path.is_file():
        raise ValueError(f"{purpose}: file not found: {path}")
    if kind == "dir" and not path.is_dir():
        raise ValueError(f"{purpose}: directory not found: {path}")
    return path


def check_run_name(name):
    if not isinstance(name, str) or not RUN_NAME_RE.match(name):
        raise ValueError(f"Invalid run name {name!r}: use 1-64 letters, digits, '_', '-' or '.', "
                         "starting with a letter or digit.")
    return name


def run_dir(name):
    """Directory of run ``name`` inside the workspace (not created)."""
    return workspace() / check_run_name(name)
