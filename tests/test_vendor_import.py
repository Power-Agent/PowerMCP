"""Tier-3 regression guard for the vendor-engine refactors.

The key invariant: importing a vendor server module on a machine WITHOUT the
vendor software must succeed and must NOT initialize the engine. The engine is
touched only by the memoized _ensure_*() helper, exactly once, on first use.
"""

from __future__ import annotations

import importlib.util
import sys
import types

from powermcp.registry import get_tool


def _load(mod_name: str, path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_psse_import_side_effect_free_then_inits_once(monkeypatch):
    init_calls = []
    fake_psspy = types.ModuleType("psspy")
    fake_psspy.psseinit = lambda n: init_calls.append(n)
    monkeypatch.setitem(sys.modules, "psspy", fake_psspy)
    monkeypatch.setitem(sys.modules, "psse36", types.ModuleType("psse36"))

    path = get_tool("psse").resolve_entry_script()
    mod = _load("psse_mcp_under_test", path)

    # Importing the module must NOT initialize the PSS/E engine.
    assert init_calls == []
    assert mod.psspy is None

    # First use initializes exactly once; second use is memoized.
    mod._ensure_psse()
    mod._ensure_psse()
    assert init_calls == [50]
    assert mod.psspy is fake_psspy

    monkeypatch.delitem(sys.modules, "psse_mcp_under_test", raising=False)


def test_pslf_import_side_effect_free_then_inits_once(monkeypatch):
    init_calls = []
    fake = types.ModuleType("PSLF_PYTHON")
    fake.init_pslf = lambda **kw: init_calls.append(kw)
    fake.Pslf = object()
    fake.CaseParameters = object()
    fake.Bus = []
    fake.Flox = []
    monkeypatch.setitem(sys.modules, "PSLF_PYTHON", fake)

    path = get_tool("pslf").resolve_entry_script()
    mod = _load("pslf_mcp_under_test", path)

    # Importing must NOT call init_pslf and must NOT require PSLF_PYTHON names yet.
    assert init_calls == []

    mod._ensure_pslf()
    mod._ensure_pslf()
    assert len(init_calls) == 1
    # The wildcard names are published into the module globals on first use.
    assert getattr(mod, "Pslf", None) is fake.Pslf
    assert hasattr(mod, "CaseParameters")

    monkeypatch.delitem(sys.modules, "pslf_mcp_under_test", raising=False)
