"""Tier-2 tests for `powermcp doctor` status logic (no real software)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys

from packaging.version import Version

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
    """A PEP 420 namespace portion must not be read as an installed library.

    This repository ships a lowercase ``surge/`` directory whose name matches
    the import name of the ``surge-py`` library. Without the library present,
    ``find_spec("surge")`` still answers -- with a namespace portion whose
    ``origin`` is None -- so a naive probe would report the dependency as
    present and ``doctor`` would tell the operator everything is fine.

    The namespace portion is simulated rather than read off the ambient
    environment. CI installs the ``surge`` extra so surge/test_integration.py
    can run, and an assertion that depended on the library being absent would
    then pass or fail for reasons having nothing to do with the logic it
    covers. Bypass surge's Python-version gate (3.12-3.14 only) so the probe
    path is exercised on every interpreter, rather than short-circuiting to the
    version warning on 3.10.
    """
    real_find_spec = importlib.util.find_spec

    def shadowed_find_spec(name, *args, **kwargs):
        if name == "surge":
            spec = importlib.machinery.ModuleSpec("surge", loader=None, origin=None)
            spec.submodule_search_locations = ["<repo>/surge"]
            return spec
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", shadowed_find_spec)
    monkeypatch.setattr(doctor, "_surge_supported", lambda: True)

    style, msg = doctor._dep_status(get_tool("surge"))
    assert style == "red", f"expected surge missing, got {style}: {msg}"


def test_tools_without_paths_show_dash():
    style, msg = doctor._path_status(get_tool("pandapower"))
    assert msg == "-"


def test_run_doctor_smoke(capsys):
    doctor.run_doctor()  # should not raise
    out = capsys.readouterr().out
    assert "PowerMCP doctor" in out


def test_install_hint_for_a_core_tool_names_no_extra():
    # powerio and the other core tools have extra=None; the hint used to render
    # `pip install powermcp[None]`, a command that does not exist.
    from powermcp.registry import install_hint

    assert install_hint(None) == "pip install powermcp"
    assert install_hint("andes") == "pip install powermcp[andes]"


def test_the_extra_survives_rich_markup(capsys):
    # Rich reads a bracketed lowercase word as a style tag and drops it, so an
    # unescaped hint printed the useless `pip install powermcp`.
    doctor.run_doctor("andes")
    out = capsys.readouterr().out
    assert "[andes]" in out.replace("\n", "").replace(" ", "")


def test_an_out_of_date_dependency_is_not_reported_ok(monkeypatch):
    # find_spec answers "importable", which is not "new enough".
    monkeypatch.setattr(doctor, "version", lambda name: "0.0.1")
    style, msg = doctor._dep_status(get_tool("powerio"))
    assert style == "red"
    assert "does not satisfy" in msg


def test_the_floor_is_found_when_the_probe_is_not_the_distribution_name():
    # A probe is an import name and a requirement names a distribution. hope
    # probes `yaml` and this project requires PyYAML>=6.0; comparing the two
    # names directly finds nothing and silently reports every version as fine.
    req = doctor._declared_requirement(get_tool("hope").probe)
    assert req is not None and doctor._canonical(req.name) == "pyyaml"
    assert str(req.specifier) == ">=6.0"


def test_the_floor_is_found_without_top_level_distribution_metadata(monkeypatch):
    monkeypatch.setattr(doctor, "_distributions", lambda probe: [])
    monkeypatch.setattr(
        doctor,
        "requires",
        lambda _distribution: ("powerio[mcp,matrix]>=0.11.2,<0.12",),
    )
    req = doctor._declared_requirement("powerio")
    assert req is not None
    assert doctor._canonical(req.name) == "powerio"
    assert Version("0.11.2") in req.specifier
    assert Version("0.11.1") not in req.specifier
    assert Version("0.12.0") not in req.specifier


def test_an_out_of_date_dependency_under_another_name_is_caught(monkeypatch):
    monkeypatch.setattr(doctor, "version", lambda name: "3.0")
    style, msg = doctor._dep_status(get_tool("hope"))
    assert style == "red"
    assert "3.0 does not satisfy" in msg and "6.0" in msg


def test_a_version_above_an_upper_bound_is_not_called_below(monkeypatch):
    monkeypatch.setattr(
        doctor, "_declared_requirement", lambda probe: doctor.Requirement("mcp>=2,<3")
    )
    monkeypatch.setattr(doctor, "version", lambda name: "3.0")

    style, msg = doctor._version_status("mcp")

    assert style == "red"
    assert "does not satisfy" in msg
    assert "below" not in msg


def test_a_version_that_does_not_parse_is_not_called_out_of_date(monkeypatch):
    # `contains` answers False for anything it cannot parse, so a malformed
    # version string would otherwise be reported as below the floor.
    monkeypatch.setattr(doctor, "version", lambda name: "not-a-version")
    assert doctor._version_status("powerio") is None


def test_the_shared_sdk_is_reported():
    style, msg = doctor._sdk_status()
    assert msg.startswith("mcp:")
    assert style == "green"


def test_containment_status_reads_every_root_spelling(tmp_path, monkeypatch):
    from powermcp.sandbox import ALLOWED_ROOTS_ENV, LEGACY_ROOT_ENVS

    for name in (ALLOWED_ROOTS_ENV,) + LEGACY_ROOT_ENVS:
        monkeypatch.delenv(name, raising=False)
    style, msg = doctor._containment_status()
    assert style == "yellow" and "startup directory" in msg

    monkeypatch.setenv(ALLOWED_ROOTS_ENV, str(tmp_path))
    style, msg = doctor._containment_status()
    assert style == "green" and str(tmp_path) in msg

    monkeypatch.setenv(ALLOWED_ROOTS_ENV, str(tmp_path / "gone"))
    style, msg = doctor._containment_status()
    assert style == "red" and "every path is refused" in msg

    # One root of several missing narrows what is reachable; it does not refuse
    # everything, and saying so would send the reader after the wrong problem.
    import os as _os

    monkeypatch.setenv(
        ALLOWED_ROOTS_ENV, _os.pathsep.join([str(tmp_path), str(tmp_path / "gone")])
    )
    style, msg = doctor._containment_status()
    assert style == "yellow"
    assert "every path is refused" not in msg
    assert str(tmp_path / "gone") in msg


def test_a_roots_variable_with_no_directory_is_refused(monkeypatch):
    from powermcp.sandbox import ALLOWED_ROOTS_ENV

    monkeypatch.setenv(ALLOWED_ROOTS_ENV, "   ")
    style, msg = doctor._containment_status()
    assert style == "red" and "at least one directory" in msg
