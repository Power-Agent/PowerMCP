"""Best-effort auto-detection of locally-installed tool software paths.

Used to prefill the install wizard (so users rarely type a path by hand) and as a
runtime fallback for servers, so a tool installed in a standard location works
even before it's explicitly configured.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _first_existing(paths) -> str | None:
    for p in paths:
        if p and Path(os.path.expanduser(p)).exists():
            return str(Path(os.path.expanduser(p)))
    return None


def ltspice_exe() -> str | None:
    """Locate the LTspice executable across the common install layouts:
    modern Analog Devices LTspice, legacy LTC LTspice XVII/IV, macOS, and Wine."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA")
    if sys.platform == "win32":
        cands = [
            rf"{pf}\ADI\LTspice\LTspice.exe",
            rf"{pf86}\ADI\LTspice\LTspice.exe",
            rf"{local}\Programs\ADI\LTspice\LTspice.exe" if local else None,
            rf"{pf}\LTC\LTspiceXVII\XVIIx64.exe",
            rf"{pf86}\LTC\LTspiceXVII\XVIIx64.exe",
            rf"{pf86}\LTC\LTspiceIV\scad3.exe",
        ]
        return _first_existing(cands)
    if sys.platform == "darwin":
        return _first_existing(["/Applications/LTspice.app/Contents/MacOS/LTspice"])
    # Linux / Wine
    home = os.path.expanduser("~")
    return _first_existing([
        f"{home}/.wine/drive_c/Program Files/ADI/LTspice/LTspice.exe",
        f"{home}/.wine/drive_c/Program Files/LTC/LTspiceXVII/XVIIx64.exe",
    ])


# Detectors keyed by "<tool>.<config_key>". Extend as other tools gain detection.
_DETECTORS = {
    "ltspice.exe": ltspice_exe,
}


def detect(tool: str, key: str) -> str | None:
    """Return an auto-detected path for a tool/config key, or None."""
    fn = _DETECTORS.get(f"{tool}.{key}")
    if fn is None:
        return None
    try:
        return fn()
    except Exception:
        return None
