"""Mocked unit tests for the SIENNA connector tools (PSCAD/tests/test_tools.py's style:
unittest + MagicMock). r2x is not installed in this environment (by design -- these tests
must pass with no PLEXOS/Sienna license and no r2x install), so every r2x_core/r2x_plexos/
r2x_sienna_to_plexos import is faked via sys.modules before each tool function runs.

run_sienna_solve is exercised here only against a mocked Julia subprocess. It was also run
for real against a genuine Julia + PowerSystems.jl 5.12.1 + PowerSimulations.jl 0.38.2 +
HiGHS.jl 1.24.1 install during development of this connector (see SIENNA/README.md and the
PR description) -- that verification is not repeated by this automated suite, which must run
without a multi-hundred-MB Julia toolchain present.
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SIENNA_ROOT = Path(__file__).resolve().parent.parent
if str(SIENNA_ROOT) not in sys.path:
    sys.path.insert(0, str(SIENNA_ROOT))

_MISSING = object()


class _patch_sys_modules:
    """Like unittest.mock.patch.dict(sys.modules, ...), but restores only the
    specific keys it touched instead of clearing/restoring the whole dict.

    mock.patch.dict's teardown unconditionally clears the target dict and
    replays a full snapshot taken at __enter__ time -- for sys.modules that
    wipes out every module imported *during* the test (e.g. mcp/pydantic
    submodules pulled in by a first-time `from mcp.server.fastmcp import
    FastMCP`), corrupting later tests in the same process. This only ever
    touches the handful of r2x_* keys we actually want to fake.
    """

    def __init__(self, mapping: dict[str, object]) -> None:
        self.mapping = mapping
        self._saved: dict[str, object] = {}

    def start(self) -> None:
        for name, mod in self.mapping.items():
            self._saved[name] = sys.modules.get(name, _MISSING)
            if mod is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    def stop(self) -> None:
        for name, original in self._saved.items():
            if original is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class _FakeComponentType:
    def __init__(self, name: str) -> None:
        self.__name__ = name


class _FakeSystem:
    """Stand-in for r2x_core.System with a couple of component types."""

    def __init__(self, counts: dict[str, int] | None = None, name: str = "fake_system") -> None:
        self._counts = counts or {"ACBus": 1, "ThermalStandard": 1, "PowerLoad": 1}
        self.name = name
        self.description = "a fake system"
        self._to_json_calls: list[str] = []

    def get_component_types(self):
        return [_FakeComponentType(n) for n in self._counts]

    def get_components(self, component_type):
        name = getattr(component_type, "__name__", str(component_type))
        return [object()] * self._counts.get(name, 0)

    def to_json(self, path):
        self._to_json_calls.append(str(path))
        Path(path).write_text(json.dumps({"name": self.name, "fake": True}))


def _install_fake_r2x_modules(counts=None, translated_counts=None):
    """Patch sys.modules with fake r2x_core/r2x_plexos/r2x_sienna_to_plexos.

    Returns the fake modules dict so tests can assert on call args.
    """
    fake_source_system = _FakeSystem(counts=counts, name="source")
    fake_translated_system = _FakeSystem(
        counts=translated_counts or {"PLEXOSNode": 1, "PLEXOSGenerator": 1},
        name="translated",
    )

    fake_r2x_core = types.ModuleType("r2x_core")
    fake_system_cls = MagicMock()
    fake_system_cls.from_json = MagicMock(return_value=fake_source_system)
    fake_r2x_core.System = fake_system_cls
    fake_r2x_core.PluginContext = MagicMock()

    fake_r2x_plexos = types.ModuleType("r2x_plexos")
    fake_r2x_plexos.PLEXOSConfig = MagicMock()
    fake_exporter_instance = MagicMock()
    fake_exporter_instance.run = MagicMock(return_value=None)
    fake_plexos_exporter_cls = MagicMock()
    fake_plexos_exporter_cls.from_context = MagicMock(return_value=fake_exporter_instance)
    fake_r2x_plexos.PLEXOSExporter = fake_plexos_exporter_cls

    fake_r2x_s2p = types.ModuleType("r2x_sienna_to_plexos")
    fake_r2x_s2p.SiennaToPlexosConfig = MagicMock()
    fake_r2x_s2p.sienna_to_plexos = MagicMock(return_value=fake_translated_system)

    return {
        "r2x_core": fake_r2x_core,
        "r2x_plexos": fake_r2x_plexos,
        "r2x_sienna_to_plexos": fake_r2x_s2p,
    }, fake_source_system, fake_translated_system


class TestLoadSystem(unittest.TestCase):
    def setUp(self):
        self.fake_modules, self.source_system, _ = _install_fake_r2x_modules()
        self.patcher = _patch_sys_modules(self.fake_modules)
        self.patcher.start()
        self.tmp = Path(__file__).resolve().parent / "_tmp_psy.json"
        self.tmp.write_text("{}")

    def tearDown(self):
        self.patcher.stop()
        self.tmp.unlink(missing_ok=True)

    def test_load_system_ok(self):
        from sienna_mcp.tools.system_tools import load_system

        result = load_system(str(self.tmp))
        self.assertTrue(result["ok"])
        self.assertEqual(result["name"], "source")
        self.assertEqual(result["component_counts"]["ACBus"], 1)
        self.assertEqual(result["total_components"], 3)

    def test_load_system_missing_file(self):
        from sienna_mcp.tools.system_tools import load_system

        result = load_system(str(self.tmp.parent / "does_not_exist.json"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "file_not_found")

    def test_load_system_r2x_not_installed(self):
        # sys.modules["r2x_core"] = None is Python's documented way to force
        # `import r2x_core` to raise ImportError (see importlib docs), simulating
        # r2x genuinely not being installed regardless of what setUp faked in.
        blocker = _patch_sys_modules({"r2x_core": None})
        blocker.start()
        try:
            from sienna_mcp.tools.system_tools import load_system

            result = load_system(str(self.tmp))
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_type"], "r2x_not_installed")
        finally:
            blocker.stop()


class TestTranslateToPlexos(unittest.TestCase):
    def setUp(self):
        self.fake_modules, self.source_system, self.translated_system = _install_fake_r2x_modules()
        self.patcher = _patch_sys_modules(self.fake_modules)
        self.patcher.start()
        self.tmp_dir = Path(__file__).resolve().parent
        self.psy = self.tmp_dir / "_tmp_psy_translate.json"
        self.psy.write_text("{}")
        self.out = self.tmp_dir / "_tmp_translated.json"

    def tearDown(self):
        self.patcher.stop()
        self.psy.unlink(missing_ok=True)
        self.out.unlink(missing_ok=True)

    def test_translate_calls_r2x_directly_and_returns_counts(self):
        from sienna_mcp.tools.translate_tools import translate_to_plexos

        result = translate_to_plexos(str(self.psy))
        self.assertTrue(result["ok"])
        self.assertEqual(result["translated_component_counts"]["PLEXOSNode"], 1)
        self.assertEqual(result["translated_total_components"], 2)

        fake_s2p_module = self.fake_modules["r2x_sienna_to_plexos"]
        fake_s2p_module.sienna_to_plexos.assert_called_once()
        called_system = fake_s2p_module.sienna_to_plexos.call_args[0][0]
        self.assertIs(called_system, self.source_system)

    def test_translate_writes_output_json(self):
        from sienna_mcp.tools.translate_tools import translate_to_plexos

        result = translate_to_plexos(str(self.psy), output_path=str(self.out))
        self.assertTrue(result["ok"])
        self.assertEqual(result["output_json_path"], str(self.out))
        self.assertIn(str(self.out), self.translated_system._to_json_calls)

    def test_translate_missing_file(self):
        from sienna_mcp.tools.translate_tools import translate_to_plexos

        result = translate_to_plexos(str(self.tmp_dir / "nope.json"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "file_not_found")

    def test_translate_failure_is_reported_not_raised(self):
        self.fake_modules["r2x_sienna_to_plexos"].sienna_to_plexos.side_effect = RuntimeError("boom")
        from sienna_mcp.tools.translate_tools import translate_to_plexos

        result = translate_to_plexos(str(self.psy))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "translate_failed")
        self.assertIn("boom", result["message"])


class TestCompareSolutions(unittest.TestCase):
    def setUp(self):
        self.fake_modules, _, _ = _install_fake_r2x_modules()
        self.patcher = _patch_sys_modules(self.fake_modules)
        self.patcher.start()
        self.tmp_dir = Path(__file__).resolve().parent

    def tearDown(self):
        self.patcher.stop()
        for name in ("_sienna_results.json", "_plexos_results.json"):
            (self.tmp_dir / name).unlink(missing_ok=True)

    def test_compare_results_json_numeric_diff(self):
        sienna_path = self.tmp_dir / "_sienna_results.json"
        plexos_path = self.tmp_dir / "_plexos_results.json"

        # Make System.from_json fail so both sides fall back to plain results JSON.
        self.fake_modules["r2x_core"].System.from_json.side_effect = ValueError("not a system")
        sienna_path.write_text(json.dumps({"objective_value": 100.0, "total_cost": 500.0}))
        plexos_path.write_text(json.dumps({"objective_value": 90.0, "total_cost": 500.0}))

        from sienna_mcp.tools.compare_tools import compare_solutions

        result = compare_solutions(str(sienna_path), str(plexos_path))
        self.assertTrue(result["ok"])
        self.assertEqual(result["metric_diff"]["objective_value"]["diff"], 10.0)
        self.assertEqual(result["metric_diff"]["total_cost"]["diff"], 0.0)

    def test_compare_system_json_component_diff(self):
        sienna_path = self.tmp_dir / "_sienna_results.json"
        plexos_path = self.tmp_dir / "_plexos_results.json"
        sienna_path.write_text("{}")
        plexos_path.write_text("{}")

        # Two calls to System.from_json: first for sienna_path, second for plexos_path.
        sienna_system = _FakeSystem(counts={"ThermalStandard": 2})
        plexos_system = _FakeSystem(counts={"PLEXOSGenerator": 1})
        self.fake_modules["r2x_core"].System.from_json.side_effect = [sienna_system, plexos_system]

        from sienna_mcp.tools.compare_tools import compare_solutions

        result = compare_solutions(str(sienna_path), str(plexos_path))
        self.assertTrue(result["ok"])
        diff = result["component_count_diff"]
        self.assertEqual(diff["ThermalStandard"], {"sienna": 2, "plexos": 0, "diff": 2})
        self.assertEqual(diff["PLEXOSGenerator"], {"sienna": 0, "plexos": 1, "diff": -1})

    def test_compare_missing_file(self):
        from sienna_mcp.tools.compare_tools import compare_solutions

        result = compare_solutions(str(self.tmp_dir / "nope1.json"), str(self.tmp_dir / "nope2.json"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["side"], "sienna")


class TestRunSiennaSolve(unittest.TestCase):
    """run_sienna_solve is mocked here (subprocess.run stubbed out); see module
    docstring for the real-Julia verification performed outside this suite."""

    def setUp(self):
        self.tmp_dir = Path(__file__).resolve().parent
        self.psy = self.tmp_dir / "_tmp_psy_solve.json"
        self.psy.write_text("{}")

    def tearDown(self):
        self.psy.unlink(missing_ok=True)

    @patch("sienna_mcp.tools.solve_tools.validate_julia_command")
    @patch("sienna_mcp.tools.solve_tools.run_julia_script")
    def test_run_sienna_solve_success(self, mock_run_script, mock_validate):
        mock_validate.return_value = ("/usr/local/bin/julia", None)

        def _fake_run(julia_bin, script_path, script_args, timeout_seconds):
            out_path = Path(script_args[1])
            out_path.write_text(json.dumps({
                "ok": True,
                "solve_status": "SUCCESSFULLY_FINALIZED",
                "objective_value": 23040.0,
            }))
            return subprocess.CompletedProcess(args=[], returncode=0, stdout="SIENNA_SOLVE_OK\n", stderr="")

        mock_run_script.side_effect = _fake_run

        from sienna_mcp.tools.solve_tools import run_sienna_solve

        result = run_sienna_solve(str(self.psy))
        self.assertTrue(result["ok"])
        self.assertEqual(result["objective_value"], 23040.0)
        self.assertEqual(result["exit_code"], 0)

    @patch("sienna_mcp.tools.solve_tools.validate_julia_command")
    def test_run_sienna_solve_julia_not_found(self, mock_validate):
        mock_validate.return_value = (None, {"ok": False, "error_type": "julia_not_found", "message": "no julia"})

        from sienna_mcp.tools.solve_tools import run_sienna_solve

        result = run_sienna_solve(str(self.psy))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "julia_not_found")

    def test_run_sienna_solve_missing_psy_file(self):
        from sienna_mcp.tools.solve_tools import run_sienna_solve

        result = run_sienna_solve(str(self.tmp_dir / "nope.json"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "file_not_found")

    @patch("sienna_mcp.tools.solve_tools.validate_julia_command")
    @patch("sienna_mcp.tools.solve_tools.run_julia_script")
    def test_run_sienna_solve_timeout(self, mock_run_script, mock_validate):
        mock_validate.return_value = ("/usr/local/bin/julia", None)
        mock_run_script.side_effect = subprocess.TimeoutExpired(cmd=["julia"], timeout=5, output="", stderr="")

        from sienna_mcp.tools.solve_tools import run_sienna_solve

        result = run_sienna_solve(str(self.psy), timeout_seconds=5)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "solve_timeout")


class TestRegisterTools(unittest.TestCase):
    """Registration smoke test -- each register_*_tools(mcp) call adds its tool."""

    def test_register_all_tools(self):
        from mcp.server.fastmcp import FastMCP

        from sienna_mcp.tools.compare_tools import register_compare_tools
        from sienna_mcp.tools.solve_tools import register_solve_tools
        from sienna_mcp.tools.system_tools import register_system_tools
        from sienna_mcp.tools.translate_tools import register_translate_tools

        mcp = FastMCP("Test")
        register_system_tools(mcp)
        register_translate_tools(mcp)
        register_solve_tools(mcp)
        register_compare_tools(mcp)
        # No assertion beyond "did not raise" -- FastMCP's tool registry is private
        # API; PSCAD's own test_tools.py takes the same approach.


if __name__ == "__main__":
    unittest.main()
