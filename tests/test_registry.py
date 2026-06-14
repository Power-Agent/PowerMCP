"""Unit tests for the powermcp.registry single source of truth."""

from __future__ import annotations

import pytest

from powermcp import registry
from powermcp.registry import CORE, TOOLS, Tool


def test_core_tools_present_and_have_no_extra():
    assert set(CORE) == {"pandapower", "pypsa", "powerio"}
    for name in CORE:
        assert TOOLS[name].extra is None


def test_every_noncore_tool_has_an_extra():
    for t in TOOLS.values():
        if t.name not in CORE:
            assert t.extra, f"{t.name} should declare a pip extra"


def test_run_kind_consistency():
    for t in TOOLS.values():
        assert t.run_kind in ("script", "module")
        if t.run_kind == "script":
            assert t.entry_rel and not t.module
        else:
            assert t.module and not t.entry_rel


def test_closed_source_path_tools_declare_config_keys():
    # PSSE/PSLF/PowerFactory/LTSpice capture a local software path; PowerWorld/PSCAD do not.
    for name in ("psse", "pslf", "powerfactory", "ltspice"):
        assert TOOLS[name].config_keys, f"{name} should declare config keys"
    assert TOOLS["powerworld"].config_keys == ()
    assert TOOLS["pscad"].config_keys == ()


def test_windows_only_flags():
    for name in ("psse", "pslf", "powerfactory", "pscad", "powerworld"):
        assert TOOLS[name].windows_only is True
    for name in ("pandapower", "pypsa", "andes", "egret", "surge", "opendss", "hope", "ltspice"):
        assert TOOLS[name].windows_only is False


def test_resolve_server_dir_exists_for_all_tools():
    for t in TOOLS.values():
        d = t.resolve_server_dir()
        assert d.is_dir(), f"{t.name}: {d} is not a directory"


def test_resolve_entry_script_exists_for_script_tools():
    for t in TOOLS.values():
        if t.run_kind == "script":
            script = t.resolve_entry_script()
            assert script.is_file(), f"{t.name}: missing entry {script}"


def test_module_tools_have_resolvable_roots():
    for t in TOOLS.values():
        if t.run_kind == "module":
            root = t.resolve_module_root()
            assert root.is_dir()
            # the module's top package dir must exist under the root
            top = t.module.split(".")[0]
            assert (root / top).is_dir(), f"{t.name}: {root / top} missing"


def test_legacy_default_lookup():
    assert registry.legacy_default("ltspice", "exe").endswith("XVIIx64.exe")
    assert registry.legacy_default("pslf", "python_lib") is None
    assert registry.legacy_default("nope", "nope") is None


def test_get_tool_unknown_raises():
    with pytest.raises(KeyError):
        registry.get_tool("does-not-exist")
