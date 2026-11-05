"""Make the PSCAD server package importable from any working directory.

``PSCAD/tests`` imports ``pscad_mcp`` as a top-level package, but pytest only
puts the test file's own directory on ``sys.path``, not the server directory
above it. The suite therefore collected only when it was invoked with ``PSCAD``
as the working directory, which is why the repository-root run CI uses could
never see it.

``tests/conftest.py`` names the ANDES server directory the same way, through
the registry; here the directory is simply this file's own parent.
"""

from __future__ import annotations

import sys
from pathlib import Path

SERVER_DIR = str(Path(__file__).resolve().parent)

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)
