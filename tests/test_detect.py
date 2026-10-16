"""Tests for powermcp.detect (auto-detection of tool software paths)."""

from __future__ import annotations

import sys

import pytest

from powermcp import detect


def test_first_existing(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    b.write_text("")
    assert detect._first_existing([str(a), str(b)]) == str(b)
    assert detect._first_existing([str(a)]) is None
    assert detect._first_existing([None, ""]) is None


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="ltspice_exe builds ProgramFiles paths with backslash separators; "
    "they only resolve on a real Windows filesystem",
)
def test_ltspice_exe_finds_adi(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    exe = tmp_path / "ADI" / "LTspice" / "LTspice.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    assert detect.ltspice_exe() == str(exe)


def test_ltspice_exe_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "pf"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "pf86"))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    assert detect.ltspice_exe() is None


def test_detect_dispatch(monkeypatch):
    assert detect.detect("nope", "nope") is None
    monkeypatch.setitem(detect._DETECTORS, "ltspice.exe", lambda: "X")
    assert detect.detect("ltspice", "exe") == "X"
    monkeypatch.setitem(detect._DETECTORS, "ltspice.exe", lambda: (_ for _ in ()).throw(OSError()))
    assert detect.detect("ltspice", "exe") is None  # detector errors are swallowed
