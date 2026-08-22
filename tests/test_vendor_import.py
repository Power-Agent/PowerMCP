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


def test_plexosdb_import_side_effect_free(monkeypatch):
    """plexosdb_mcp.main is an always-imports thin re-export (like powerio_mcp.py),
    not a lazy _ensure_*() style module -- so "side-effect-free" here means the
    module builds its FastMCP server using only the (mocked) upstream
    plexosdb_mcp.server factory, with no real plexosdb database opened, no
    PLEXOS XML touched, and no PLEXOS license required.

    plexosdb_mcp is a package name shared with the upstream ``plexosdb-mcp``
    distribution PowerMCP re-exports (see the registry's "plexosdb" entry
    comment on why it launches as a script rather than a module), so we
    monkeypatch sys.modules the same way test_psse/test_pslf do for their
    vendor packages, rather than requiring the real thing to be installed.
    """
    build_calls = []

    class FakeMCP:
        def __init__(self) -> None:
            self.registered: list[str] = []

        def tool(self):
            def decorator(fn):
                self.registered.append(fn.__name__)
                return fn

            return decorator

    def fake_build_mcp_server(state=None, *, read_only=None):
        build_calls.append((state, read_only))
        return FakeMCP()

    fake_server = types.ModuleType("plexosdb_mcp.server")
    fake_server.MCPServerState = type("MCPServerState", (), {})
    fake_server.build_mcp_server = fake_build_mcp_server
    fake_server.main = lambda argv=None: None

    fake_pkg = types.ModuleType("plexosdb_mcp")
    fake_pkg.__path__ = []  # mark as a package so `from plexosdb_mcp import server` resolves
    fake_pkg.server = fake_server

    monkeypatch.setitem(sys.modules, "plexosdb_mcp", fake_pkg)
    monkeypatch.setitem(sys.modules, "plexosdb_mcp.server", fake_server)

    path = get_tool("plexosdb").resolve_entry_script()
    mod = _load("plexosdb_mcp_under_test", path)

    # Importing must not open a real PLEXOS database or require plexosdb/r2x to
    # be installed: only the mocked build_mcp_server was ever called, exactly once.
    assert len(build_calls) == 1
    # Both of PowerMCP's own tools registered onto the (fake) re-exported server,
    # alongside whatever the upstream server itself would have registered.
    assert mod.mcp.registered == ["translate_to_sienna", "compare_solutions"]
    # r2x (r2x_core/r2x_plexos/r2x_sienna) is imported lazily inside the tool
    # function bodies, not at module import time -- reaching this line at all,
    # with no r2x package installed, is the proof.

    monkeypatch.delitem(sys.modules, "plexosdb_mcp_under_test", raising=False)


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
