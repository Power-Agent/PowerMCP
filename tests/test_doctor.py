"""Tier-2 tests for `powermcp doctor` status logic (no real software)."""

from __future__ import annotations

import sys

from powermcp import doctor
from powermcp.registry import get_tool


def test_core_deps_report_ok():
    # pandapower + pypsa are installed in the test venv.
    for name in ("pandapower", "pypsa"):
        style, msg = doctor._dep_status(get_tool(name))
        assert (style, msg) == ("green", "ok")


def test_missing_extra_reports_install_hint(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")  # keep andes visible regardless
    style, msg = doctor._dep_status(get_tool("andes"))
    # andes is not installed in the core test venv
    assert style == "red"
    assert "pip install powermcp[andes]" in msg


def test_path_loaded_engines_not_import_probed(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    for name in ("psse", "pslf", "powerfactory"):
        style, msg = doctor._dep_status(get_tool(name))
        assert "vendor engine" in msg


def test_windows_only_skipped_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    style, msg = doctor._dep_status(get_tool("psse"))
    assert "Windows-only" in msg


def test_surge_python_gate(monkeypatch):
    monkeypatch.setattr(doctor, "_surge_supported", lambda: False)
    style, msg = doctor._dep_status(get_tool("surge"))
    assert style == "yellow" and "3.12" in msg


def test_path_status_missing_and_configured(isolated_config):
    from powermcp import config as cfg

    # ltspice.exe unset -> reported as needing config
    style, msg = doctor._path_status(get_tool("ltspice"))
    assert style == "yellow" and "ltspice.exe" in msg

    # set it (must_exist is enforced; point at a real file)
    target = isolated_config / "LTspice.exe"
    target.write_text("")
    cfg.set_value("ltspice", "exe", str(target))
    style, msg = doctor._path_status(get_tool("ltspice"))
    assert style == "green"


def test_namespace_shadow_not_false_positive(monkeypatch):
    # surge-py is NOT installed in the test venv. The repo's lowercase surge/
    # directory must not be mistaken for the installed library (PEP 420 namespace
    # shadow), so the dependency must report missing, not ok. Bypass surge's
    # Python-version gate (it is 3.12-3.14 only) so this exercises the probe path
    # on every Python version — otherwise on 3.10/3.11 _dep_status short-circuits
    # to the "needs Python 3.12-3.14" warning before reaching the probe.
    monkeypatch.setattr(doctor, "_surge_supported", lambda: True)
    style, msg = doctor._dep_status(get_tool("surge"))
    assert style == "red", f"expected surge missing, got {style}: {msg}"


def test_tools_without_paths_show_dash():
    style, msg = doctor._path_status(get_tool("pandapower"))
    assert msg == "—"


def test_run_doctor_smoke(capsys):
    doctor.run_doctor()  # should not raise
    out = capsys.readouterr().out
    assert "PowerMCP doctor" in out
