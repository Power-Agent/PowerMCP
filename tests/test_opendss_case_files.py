"""The shipped OpenDSS cases must compile on case-sensitive filesystems.

Windows and macOS resolve ``redirect IEEELineCodes.dss`` against a file named
``IEEELineCodes.DSS``; Linux does not, and OpenDSS then leaves a circuit with
no line codes. Compare names exactly so the check fails on every platform.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

OPENDSS_DIR = Path(__file__).resolve().parents[1] / "OpenDSS"
_FILE_COMMAND = re.compile(r"^\s*(redirect|compile|buscoords)\s+(\S+)", re.IGNORECASE)


def _dss_files():
    return sorted(p for p in OPENDSS_DIR.rglob("*") if p.suffix.lower() == ".dss")


def _referenced_files(dss_file: Path):
    for line in dss_file.read_text(errors="replace").splitlines():
        match = _FILE_COMMAND.match(line)
        if match:
            yield match.group(2).strip("\"'()[]")


def _exists_with_exact_case(base: Path, relative: str) -> bool:
    current = base
    for part in Path(relative.replace("\\", "/")).parts:
        if part in (".", ".."):
            current = current / part
            continue
        if not current.is_dir() or part not in {entry.name for entry in current.iterdir()}:
            return False
        current = current / part
    return current.is_file()


@pytest.mark.parametrize("dss_file", _dss_files(), ids=lambda p: str(p.relative_to(OPENDSS_DIR)))
def test_referenced_files_match_case_exactly(dss_file):
    missing = [
        target
        for target in _referenced_files(dss_file)
        if not _exists_with_exact_case(dss_file.parent, target)
    ]
    assert not missing, f"{dss_file.name} references files that do not exist with this exact case: {missing}"
