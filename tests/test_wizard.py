"""Tier-2 tests for the install wizard's tool selection / platform filtering."""

from __future__ import annotations

import sys
import types

import pytest

from powermcp import wizard
from powermcp.registry import CORE


def test_yes_mode_selects_core_only():
    selected = wizard._resolve_selection(yes=True, tools=None, select_all=False, client_names=[])
    assert [t.name for t in selected] == list(CORE)


def test_tools_flag_includes_requested_plus_core(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")  # make psse available
    names = {t.name for t in wizard._resolve_selection(yes=False, tools="psse,andes", select_all=False, client_names=[])}
    assert {"psse", "andes"} <= names  # explicit picks present
    assert set(CORE) <= names          # core always included


def test_tools_all_keyword_and_all_flag(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(wizard, "_surge_supported", lambda: True)
    via_keyword = {t.name for t in wizard._resolve_selection(yes=False, tools="all", select_all=False, client_names=[])}
    via_flag = {t.name for t in wizard._resolve_selection(yes=False, tools=None, select_all=True, client_names=[])}
    assert via_keyword == via_flag
    assert {"psse", "pslf", "powerfactory", "pscad", "ltspice", "andes"} <= via_keyword


def test_tools_unknown_id_ignored_not_fatal():
    names = {t.name for t in wizard._resolve_selection(yes=False, tools="pandapower,bogustool", select_all=False, client_names=[])}
    assert "pandapower" in names
    assert "bogustool" not in names


def test_tools_unavailable_off_platform_skipped(monkeypatch):
    # psse is Windows-only: requesting it on Linux drops it, leaving core only.
    monkeypatch.setattr(sys, "platform", "linux")
    names = {t.name for t in wizard._resolve_selection(yes=False, tools="psse", select_all=False, client_names=[])}
    assert "psse" not in names
    assert set(CORE) <= names


def test_windows_only_hidden_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    names = {t.name for t in wizard.selectable_tools()}
    for win_tool in ("psse", "pslf", "powerfactory", "pscad", "powerworld"):
        assert win_tool not in names
    for ok_tool in ("pandapower", "pypsa", "andes", "egret", "opendss", "hope", "ltspice"):
        assert ok_tool in names


def test_windows_only_shown_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(wizard, "_surge_supported", lambda: True)
    names = {t.name for t in wizard.selectable_tools()}
    assert {"psse", "pslf", "powerfactory", "pscad", "powerworld"} <= names


def test_surge_hidden_when_python_unsupported(monkeypatch):
    monkeypatch.setattr(wizard, "_surge_supported", lambda: False)
    assert "surge" not in {t.name for t in wizard.selectable_tools()}


def test_is_installed_or_configured(isolated_config):
    from powermcp import config as cfg

    # pandapower is installed in the test venv → counts as set up.
    assert wizard._is_installed_or_configured(wizard.TOOLS["pandapower"]) is True
    # psse has no pip probe; unset paths → not set up, then set them → set up.
    assert wizard._is_installed_or_configured(wizard.TOOLS["psse"]) is False
    cfg.set_value("psse", "python_lib", r"C:\x\PSSPY311")
    cfg.set_value("psse", "bin", r"C:\x\PSSBIN")
    assert wizard._is_installed_or_configured(wizard.TOOLS["psse"]) is True


def test_existing_managed_tools_reads_client_config(tmp_path, monkeypatch):
    import json

    from powermcp.clients import claude_desktop

    cfg_file = tmp_path / "claude_desktop_config.json"
    cfg_file.write_text(
        json.dumps({"mcpServers": {
            "powermcp_andes": {"command": "x", "args": []},
            "filesystem": {"command": "y", "args": []},   # foreign, ignored
        }}),
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_desktop, "config_path", lambda: cfg_file)
    assert wizard._existing_managed_tools(["claude-desktop"]) == {"andes"}


def test_preselected_includes_core_installed_and_existing(tmp_path, monkeypatch, isolated_config):
    import json

    from powermcp.clients import claude_desktop

    monkeypatch.setattr(sys, "platform", "win32")
    cfg_file = tmp_path / "claude_desktop_config.json"
    cfg_file.write_text(
        json.dumps({"mcpServers": {"powermcp_andes": {"command": "x", "args": []}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(claude_desktop, "config_path", lambda: cfg_file)
    pre = wizard._preselected_names(["claude-desktop"])
    assert set(CORE) <= pre              # core always
    assert "andes" in pre                # already in the client config
    assert "pslf" not in pre             # not installed, not configured, not in client


def test_interactive_select_non_tty_returns_core(monkeypatch):
    monkeypatch.setattr(wizard, "_tty", lambda: False)
    assert [t.name for t in wizard._interactive_select([])] == list(CORE)


def test_capture_paths_non_tty_does_not_prompt(monkeypatch, capsys):
    # No TTY: must not import/use questionary, must not raise, and should tell the
    # user how to set the path manually.
    monkeypatch.setattr(wizard, "_tty", lambda: False)
    monkeypatch.setitem(sys.modules, "questionary", None)  # any use would raise
    wizard._capture_paths([wizard.TOOLS["psse"]])
    out = capsys.readouterr().out
    assert "powermcp config set psse.python_lib" in out


def test_interactive_select_ctrl_c_returns_empty(monkeypatch):
    # TTY present but the user aborts the picker (questionary returns None).
    monkeypatch.setattr(wizard, "_tty", lambda: True)
    fake_q = types.ModuleType("questionary")

    class _Q:
        def ask(self):
            return None

    fake_q.Choice = lambda **kw: kw
    fake_q.checkbox = lambda *a, **k: _Q()
    monkeypatch.setitem(sys.modules, "questionary", fake_q)
    assert wizard._interactive_select([]) == []
