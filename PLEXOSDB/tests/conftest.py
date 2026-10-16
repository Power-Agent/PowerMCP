"""Name the roots this suite's fixture paths live under.

powerio 0.11.2 confines MCP paths to the directory the server process started
in when no root variable names one. ``translate_to_sienna`` and
``compare_solutions`` both run their arguments through ``checked_path`` before
touching r2x, so an absolute fixture path is refused and the tool returns its
``PathNotAllowed`` shape -- carrying neither ``ok`` nor ``identical`` -- before
the mocked pipeline is reached.

``tests/conftest.py`` names roots the same way for the repository-root suite.
The roots are resolved through ``realpath`` because the policy compares real
targets, and ``/tmp`` is a symlink on macOS.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from powermcp.sandbox import ALLOWED_ROOTS_ENV, LEGACY_ROOT_ENVS


@pytest.fixture(scope="session", autouse=True)
def mcp_allowed_roots():
    """Allow the temporary tree the fixture paths are built under."""
    roots = [os.path.realpath(tempfile.gettempdir())]
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(ALLOWED_ROOTS_ENV, os.pathsep.join(dict.fromkeys(roots)))
        for name in LEGACY_ROOT_ENVS:
            patch.delenv(name, raising=False)
        yield
