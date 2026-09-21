"""Name the roots this suite writes to.

The format round-trip and export checks save networks and CSV tables into
``tempfile.TemporaryDirectory()`` trees. powerio 0.11.2 confines MCP paths to
the directory the server process started in when no root variable names one,
so ``save_network`` and ``export_tables`` refuse a temporary path and answer
with an error instead of writing.

Those sub-checks only tallied their failures rather than raising, so the suite
reported green while nothing was written. ``tests/conftest.py`` names roots the
same way for the repository-root suite.

The variable is set in the environment rather than in-process because one
export check runs its assertion in a subprocess, which inherits it.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from powermcp.sandbox import ALLOWED_ROOTS_ENV, LEGACY_ROOT_ENVS


@pytest.fixture(scope="session", autouse=True)
def mcp_allowed_roots():
    """Allow the temporary tree these checks write into.

    Resolved through ``realpath`` because the policy compares real targets and
    ``/tmp`` is a symlink on macOS.
    """
    roots = [os.path.realpath(tempfile.gettempdir())]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(ALLOWED_ROOTS_ENV, os.pathsep.join(dict.fromkeys(roots)))
        for name in LEGACY_ROOT_ENVS:
            patch.delenv(name, raising=False)
        yield
