"""Tests for powermcp.runner — launching servers without starting a real server.

We monkeypatch FastMCP.run so the server module executes its full import + tool
registration but the stdio loop is a no-op (records the call instead).
"""

from __future__ import annotations

import sys

import pytest

from powermcp import runner


@pytest.fixture()
def record_mcp_run(monkeypatch):
    calls = []

    def fake_run(self, *args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("mcp.server.fastmcp.FastMCP.run", fake_run, raising=True)
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
    # After launching, `import pandapower` must still resolve to the installed
    # library (a real package with pandapowerNet), not the server directory.
    runner.launch("pandapower")
    import pandapower as pp

    assert hasattr(pp, "create_empty_network")


def test_preflight_missing_pip_dep_raises():
    # andes is an opt-in extra and is not installed in the test venv.
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
    # Reproduces the mhi.pscad case: `ns` is a PEP 420 namespace (no __init__),
    # `ns.sub` is a real package. Probing the full dotted name must succeed even
    # though the top-level parent is a namespace; a bare namespace must not.
    (tmp_path / "ns" / "sub").mkdir(parents=True)
    (tmp_path / "ns" / "sub" / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    for m in ("ns", "ns.sub"):
        sys.modules.pop(m, None)
    try:
        assert runner.probe_installed("ns.sub") is True   # real subpackage (like mhi.pscad)
        assert runner.probe_installed("ns") is False       # bare namespace (like the surge shadow)
        assert runner.probe_installed("definitely_absent_pkg_xyz") is False
    finally:
        for m in ("ns", "ns.sub"):
            sys.modules.pop(m, None)


def test_python_dash_m_powermcp_works():
    # Regression: MCP client configs launch via `python -m powermcp run <tool>`,
    # which requires powermcp/__main__.py. Exercise that exact entry path.
    import subprocess

    r = subprocess.run(
        [sys.executable, "-m", "powermcp", "--version"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert "powermcp" in r.stdout
