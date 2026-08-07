"""Unit tests for PLEXOSDB/plexosdb_mcp/main.py's own tools, mocking r2x
directly (PSCAD/tests/test_tools.py's MagicMock style) so these tests need no
PLEXOS license, no PLEXOS install, and no real r2x/plexosdb packages present.

These tests import ``plexosdb_mcp.main`` the same way tests/test_vendor_import.py
does at the repo root: with the upstream ``plexosdb_mcp.server`` module faked in
sys.modules first, since our own connector package is deliberately also named
``plexosdb_mcp`` (it thin-re-exports the upstream package of the same name) and
must not require that upstream package -- or a real PLEXOS/plexosdb install --
to be importable and unit-testable.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

MAIN_PATH = Path(__file__).resolve().parent.parent / "plexosdb_mcp" / "main.py"


class FakeMCP:
    """Minimal FastMCP stand-in: records tool functions under their own name
    and lets tests call them directly, exactly as PSCAD's tests call the
    plain async/sync functions registered by register_*_tools()."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator

    def run(self, *args, **kwargs):  # pragma: no cover - not exercised in tests
        raise AssertionError("mcp.run() should not be called from unit tests")


def _load_main_module():
    """Load plexosdb_mcp/main.py with the upstream plexosdb_mcp.server package
    faked, so import needs neither the real (git-installed) plexosdb-mcp nor a
    PLEXOS license/install."""
    fake_server = types.ModuleType("plexosdb_mcp.server")
    fake_server.MCPServerState = type("MCPServerState", (), {})
    fake_server.build_mcp_server = lambda state=None, **kw: FakeMCP()
    fake_server.main = lambda argv=None: None

    fake_pkg = types.ModuleType("plexosdb_mcp")
    fake_pkg.__path__ = []
    fake_pkg.server = fake_server

    sys.modules["plexosdb_mcp"] = fake_pkg
    sys.modules["plexosdb_mcp.server"] = fake_server

    spec = importlib.util.spec_from_file_location("plexosdb_main_under_test", str(MAIN_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["plexosdb_main_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestTranslateToSienna(unittest.TestCase):
    """translate_to_sienna calls r2x's real, public API directly (PLEXOSParser
    -> plexos_to_sienna -> SiennaExporter); mock each stage's entry point at
    the module it's imported from, matching how PSCAD's tests mock
    pscad_manager rather than reimplementing PSCAD's own internals."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_main_module()

    def test_translate_to_sienna_calls_r2x_pipeline_and_summarizes_components(self):
        fake_source_system = MagicMock(name="plexos_system")
        fake_sienna_system = MagicMock(name="sienna_system")

        class Bus:
            pass

        class Generator:
            pass

        fake_sienna_system.get_component_types.return_value = [Bus, Generator]
        fake_sienna_system.get_components.side_effect = lambda ct: (
            [object(), object()] if ct is Bus else [object()]
        )

        fake_parse_ctx = MagicMock()
        fake_parse_ctx.system = fake_source_system

        fake_parser_instance = MagicMock()
        fake_parser_instance.run.return_value = fake_parse_ctx

        with (
            patch.dict(
                sys.modules,
                {
                    "r2x_core": MagicMock(PluginContext=MagicMock(side_effect=lambda **kw: kw)),
                    "r2x_plexos": MagicMock(),
                    "r2x_plexos_to_sienna": MagicMock(),
                    "r2x_sienna": MagicMock(),
                },
            ),
        ):
            import r2x_plexos
            import r2x_plexos_to_sienna
            import r2x_sienna

            r2x_plexos.PLEXOSParser.from_context.return_value = fake_parser_instance
            r2x_plexos_to_sienna.plexos_to_sienna.return_value = fake_sienna_system

            fake_export_ctx = MagicMock()
            r2x_sienna.SiennaExporter.from_context.return_value = fake_export_ctx

            result = self.mod.translate_to_sienna(
                xml_path="/data/study.xml",
                model_name="Base",
                output_path="/tmp/out/system.json",
            )

        r2x_plexos_to_sienna.plexos_to_sienna.assert_called_once_with(
            fake_source_system, r2x_plexos_to_sienna.PlexosToSiennaConfig.return_value
        )
        fake_export_ctx.run.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["output_path"], "/tmp/out/system.json")
        self.assertEqual(result["component_types"], {"Bus": 2, "Generator": 1})


class TestCompareSolutions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_main_module()

    def test_compare_solutions_reports_no_differences_for_identical_models(self):
        class Bus:
            pass

        fake_system = MagicMock()
        fake_system.get_component_types.return_value = [Bus]
        fake_system.get_components.return_value = [object(), object()]

        fake_ctx = MagicMock()
        fake_ctx.system = fake_system
        fake_parser_instance = MagicMock()
        fake_parser_instance.run.return_value = fake_ctx

        with patch.dict(
            sys.modules,
            {
                "r2x_core": MagicMock(PluginContext=MagicMock(side_effect=lambda **kw: kw)),
                "r2x_plexos": MagicMock(),
            },
        ):
            import r2x_plexos

            r2x_plexos.PLEXOSParser.from_context.return_value = fake_parser_instance

            result = self.mod.compare_solutions(
                xml_path_a="/data/study.xml",
                model_name_a="Base",
                xml_path_b="/data/study.xml",
                model_name_b="Base",
            )

        self.assertTrue(result["identical"])
        self.assertEqual(result["differences"], {})
        self.assertEqual(result["model_a"]["component_types"], {"Bus": 2})
        self.assertEqual(result["model_b"]["component_types"], {"Bus": 2})

    def test_compare_solutions_reports_a_count_difference(self):
        class Bus:
            pass

        counts = iter([2, 3])

        def fake_get_components(ct):
            return [object()] * next(counts)

        fake_system = MagicMock()
        fake_system.get_component_types.return_value = [Bus]
        fake_system.get_components.side_effect = fake_get_components

        fake_ctx = MagicMock()
        fake_ctx.system = fake_system
        fake_parser_instance = MagicMock()
        fake_parser_instance.run.return_value = fake_ctx

        with patch.dict(
            sys.modules,
            {
                "r2x_core": MagicMock(PluginContext=MagicMock(side_effect=lambda **kw: kw)),
                "r2x_plexos": MagicMock(),
            },
        ):
            import r2x_plexos

            r2x_plexos.PLEXOSParser.from_context.return_value = fake_parser_instance

            result = self.mod.compare_solutions(
                xml_path_a="/data/a.xml",
                model_name_a="Base",
                xml_path_b="/data/b.xml",
                model_name_b="Base",
            )

        self.assertFalse(result["identical"])
        self.assertEqual(result["differences"], {"Bus": {"a": 2, "b": 3}})


class TestUpstreamReExport(unittest.TestCase):
    """The re-exported plexosdb-mcp tools themselves are not PowerMCP's to unit
    test (they belong to the upstream project); this only checks the shape of
    the re-export, matching powerio_mcp.py's own precedent."""

    def test_mcp_and_upstream_names_are_re_exported(self):
        mod = _load_main_module()
        self.assertIn("mcp", mod.__all__)
        self.assertIn("MCPServerState", mod.__all__)
        self.assertIn("build_mcp_server", mod.__all__)
        self.assertIn("translate_to_sienna", mod.__all__)
        self.assertIn("compare_solutions", mod.__all__)
        # Both new tools registered onto the (fake) server built at import time.
        self.assertIn("translate_to_sienna", mod.mcp.tools)
        self.assertIn("compare_solutions", mod.mcp.tools)


if __name__ == "__main__":
    unittest.main()
