"""Tests for powermcp.runner — launching servers without starting a real server.

We monkeypatch FastMCP.run so the server module executes its full import + tool
registration but the stdio loop is a no-op (records the call instead).
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from powermcp import runner
from powermcp.registry import Tool


@pytest.fixture()
def record_mcp_run(monkeypatch):
    calls = []

    def fake_run(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("mcp.server.mcpserver.MCPServer.run", fake_run, raising=True)
    return calls


def test_launch_pandapower_runs_once(record_mcp_run):
    runner.launch("pandapower")
    assert len(record_mcp_run) == 1
    _, kwargs = record_mcp_run[0]
    assert kwargs.get("transport") == "stdio"


def test_launch_pypsa_runs_once(record_mcp_run):
    runner.launch("pypsa")
    assert len(record_mcp_run) == 1


def test_launch_does_not_shadow_installed_library(record_mcp_run):
    runner.launch("pandapower")
    import pandapower as pp

    assert hasattr(pp, "create_empty_network")


def test_preflight_missing_pip_dep_raises():
    with pytest.raises(runner.LaunchError) as exc:
        runner.launch("andes")
    assert "powermcp[andes]" in str(exc.value)


def test_preflight_windows_only_rejected_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(runner.LaunchError) as exc:
        runner.launch("psse")
    assert "Windows-only" in str(exc.value)


def test_unknown_tool_raises():
    with pytest.raises(KeyError):
        runner.launch("nope")


def test_probe_installed_handles_namespace_parent(tmp_path, monkeypatch):
    (tmp_path / "ns" / "sub").mkdir(parents=True)
    (tmp_path / "ns" / "sub" / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    for m in ("ns", "ns.sub"):
        sys.modules.pop(m, None)
    try:
        assert runner.probe_installed("ns.sub") is True
        assert runner.probe_installed("ns") is False
        assert runner.probe_installed("definitely_absent_pkg_xyz") is False
    finally:
        for m in ("ns", "ns.sub"):
            sys.modules.pop(m, None)


def test_python_dash_m_powermcp_works():
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "powermcp", "--version"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "powermcp" in r.stdout


def test_preflight_missing_sdk_raises(monkeypatch):
    real = runner.probe_installed
    monkeypatch.setattr(
        runner, "probe_installed", lambda p: False if p == "mcp" else real(p)
    )
    with pytest.raises(runner.LaunchError) as exc:
        runner.launch("powerio")
    assert "MCP SDK is not installed" in str(exc.value)


def test_launch_powerio_runs_powerios_own_module(record_mcp_run, monkeypatch):
    seen = []
    real = runner.runpy.run_module

    def spy(mod, **kwargs):
        seen.append(mod)
        return real(mod, **kwargs)

    monkeypatch.setattr(runner.runpy, "run_module", spy)
    runner.launch("powerio")
    assert seen == ["powerio.mcp"]
    assert len(record_mcp_run) == 1


def _tool(kind: str, *, server_dir: str = "example", module_root_rel: str | None = None) -> Tool:
    return Tool(
        name=f"test-{kind}", display="test", kind="open-source",
        windows_only=False, extra=None, server_dir=server_dir,
        run_kind=kind, entry_rel="server.py" if kind == "script" else None,
        module="example.main" if kind == "module" else ("powerio.mcp" if kind == "package" else None),
        module_root_rel=module_root_rel,
    )


@pytest.mark.parametrize("kind", ["script", "module", "package"])
def test_temporary_import_paths_are_restored_after_success(monkeypatch, kind, tmp_path):
    original = list(sys.path)
    temp = str(tmp_path)
    monkeypatch.setattr(runner, "get_tool", lambda _name: _tool(kind))
    monkeypatch.setattr(runner, "_preflight", lambda _tool: None)
    monkeypatch.setattr(runner.Tool, "resolve_entry_script", lambda _self: SimpleNamespace(parent=tmp_path))
    monkeypatch.setattr(runner.Tool, "resolve_module_root", lambda _self: tmp_path)
    monkeypatch.setattr(runner.runpy, "run_path", lambda *_a, **_k: None)
    monkeypatch.setattr(runner.runpy, "run_module", lambda *_a, **_k: None)

    runner.launch("ignored")
    assert sys.path == original
    if kind == "package":
        assert temp not in sys.path


@pytest.mark.parametrize("kind", ["script", "module"])
def test_temporary_import_paths_are_restored_when_launch_raises(monkeypatch, kind, tmp_path):
    original = list(sys.path)
    monkeypatch.setattr(runner, "get_tool", lambda _name: _tool(kind))
    monkeypatch.setattr(runner, "_preflight", lambda _tool: None)
    monkeypatch.setattr(runner.Tool, "resolve_entry_script", lambda _self: SimpleNamespace(parent=tmp_path))
    monkeypatch.setattr(runner.Tool, "resolve_module_root", lambda _self: tmp_path)

    def fail(*_args, **_kwargs):
        raise RuntimeError("simulated startup failure")

    monkeypatch.setattr(runner.runpy, "run_path", fail)
    monkeypatch.setattr(runner.runpy, "run_module", fail)
    with pytest.raises(RuntimeError, match="simulated startup failure"):
        runner.launch("ignored")
    assert sys.path == original


@pytest.mark.parametrize(
    "mutation",
    [
        lambda path: sys.path.append("server-added-entry"),
        lambda path: sys.path.remove(path),
        lambda path: sys.path.insert(0, "server-reordered-entry"),
        lambda path: sys.path.append(path),
    ],
)
def test_temporary_sys_path_restores_exact_state_after_server_mutation(tmp_path, mutation):
    original = sys.path[:]
    entry = str(tmp_path)
    try:
        with runner._temporary_sys_path(entry):
            mutation(entry)
        assert sys.path == original
    finally:
        sys.path[:] = original


def test_temporary_sys_path_preserves_preexisting_entries(tmp_path):
    entry = str(tmp_path)
    original = list(sys.path)
    sys.path.insert(0, entry)
    try:
        with runner._temporary_sys_path(entry):
            assert sys.path.count(entry) == 1
        assert sys.path == [entry, *original]
    finally:
        sys.path[:] = original
