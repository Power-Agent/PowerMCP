"""The PLEXOSDB tools report r2x failures rather than raising them.

r2x is not installed in CI and needs a real PLEXOS XML study, so the r2x
packages the two tools import are substituted with fakes that raise. What is
under test is the shape the tool hands back, not the translation itself.
"""

from __future__ import annotations

import importlib.util
import sys
import types

import pytest

from powermcp.registry import get_tool


@pytest.fixture()
def plexosdb(monkeypatch):
    """The connector module, built on a substituted upstream server."""
    from mcp.server.mcpserver import MCPServer

    upstream = types.ModuleType("plexosdb_mcp.server")
    upstream.MCPServerState = type("MCPServerState", (), {})
    upstream.build_mcp_server = lambda: MCPServer("plexosdb")
    upstream.main = lambda argv=None: None

    package = types.ModuleType("plexosdb_mcp")
    package.__path__ = []
    package.server = upstream

    monkeypatch.setitem(sys.modules, "plexosdb_mcp", package)
    monkeypatch.setitem(sys.modules, "plexosdb_mcp.server", upstream)

    path = get_tool("plexosdb").resolve_entry_script()
    spec = importlib.util.spec_from_file_location("plexosdb_main_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "plexosdb_main_under_test", module)
    spec.loader.exec_module(module)
    return module


def _fake_r2x(monkeypatch, exception: Exception) -> None:
    """Install r2x packages whose parser raises on use."""

    class Parser:
        @staticmethod
        def from_context(context):
            raise exception

    monkeypatch.setitem(
        sys.modules,
        "r2x_core",
        types.SimpleNamespace(PluginContext=lambda **kwargs: object()),
    )
    monkeypatch.setitem(
        sys.modules,
        "r2x_plexos",
        types.SimpleNamespace(
            PLEXOSConfig=lambda **kwargs: object(), PLEXOSParser=Parser
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "r2x_plexos_to_sienna",
        types.SimpleNamespace(
            PlexosToSiennaConfig=object, plexos_to_sienna=lambda *a, **k: None
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "r2x_sienna",
        types.SimpleNamespace(SiennaExporter=object, SiennaExporterConfig=object),
    )


def test_an_r2x_failure_in_translate_is_reported_not_raised(
    plexosdb, monkeypatch, tmp_path
):
    """An r2x exception reaches the caller as a result, naming its type."""
    study = tmp_path / "Study.xml"
    study.write_text("<MasterDataSet />")
    _fake_r2x(monkeypatch, KeyError("Horizon"))

    result = plexosdb.translate_to_sienna(
        xml_path=str(study),
        model_name="Base",
        output_path=str(tmp_path / "system.json"),
    )
    assert result["status"] == "error"
    assert result["message"] == "KeyError: 'Horizon'"


def test_an_r2x_failure_in_compare_is_reported_not_raised(
    plexosdb, monkeypatch, tmp_path
):
    study = tmp_path / "Study.xml"
    study.write_text("<MasterDataSet />")
    _fake_r2x(monkeypatch, RuntimeError("model 'Peak' was not found"))

    result = plexosdb.compare_solutions(
        xml_path_a=str(study),
        model_name_a="Base",
        xml_path_b=str(study),
        model_name_b="Peak",
    )
    assert result["status"] == "error"
    assert "model 'Peak' was not found" in result["message"]


@pytest.mark.parametrize("tool_name", ["translate_to_sienna", "compare_solutions"])
def test_a_path_outside_the_allowed_roots_is_refused(
    plexosdb, monkeypatch, tmp_path, tool_name
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "Study.xml").write_text("<MasterDataSet />")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    arguments = {
        "translate_to_sienna": {
            "xml_path": str(outside / "Study.xml"),
            "model_name": "Base",
            "output_path": str(allowed / "system.json"),
        },
        "compare_solutions": {
            "xml_path_a": str(outside / "Study.xml"),
            "model_name_a": "Base",
            "xml_path_b": str(outside / "Study.xml"),
            "model_name_b": "Peak",
        },
    }[tool_name]

    result = getattr(plexosdb, tool_name)(**arguments)
    assert result["status"] == "error"
    assert "xml_path" in result["message"]


def test_a_refused_path_is_reported_before_r2x_is_imported(
    plexosdb, monkeypatch, tmp_path
):
    """Containment runs first, so no r2x package has to be importable."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))
    for name in ("r2x_core", "r2x_plexos", "r2x_plexos_to_sienna", "r2x_sienna"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    result = plexosdb.translate_to_sienna(
        xml_path=str(tmp_path / "outside.xml"),
        model_name="Base",
        output_path=str(allowed / "system.json"),
    )
    assert result["status"] == "error"
    assert "xml_path" in result["message"]
