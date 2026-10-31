"""Offline FT-35 reproducibility checks; never import a licensed PF engine."""

import ast
import importlib.util
import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"
SPEC = importlib.util.spec_from_file_location(
    "zip_rms_diagnostic", EVIDENCE / "scripts" / "lab_zip_rms_diagnostic.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class RmsZipEvidenceTest(unittest.TestCase):
    def assert_analysis_equal(self, actual, expected):
        self.assertIs(type(actual), type(expected))
        if isinstance(expected, dict):
            self.assertEqual(actual.keys(), expected.keys())
            for key in expected:
                self.assert_analysis_equal(actual[key], expected[key])
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for value, reference in zip(actual, expected):
                self.assert_analysis_equal(value, reference)
        elif isinstance(expected, float):
            # Python versions can accumulate settled-window means differently.
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                            f"{actual!r} != {expected!r} within roundoff tolerance")
        else:
            self.assertEqual(actual, expected)

    def test_analysis_comparison_tolerates_only_float_roundoff(self):
        expected = {"windows": [{"p_mw": 0.9006952645048028}],
                    "passed": True, "count": 3, "mode": "zip", "error": None}
        actual = dict(expected, windows=[{"p_mw": 0.9006952645048024}])
        self.assert_analysis_equal(actual, expected)
        for changed in (dict(expected, windows=[{"p_mw": 0.9006953}]),
                        dict(expected, passed=False), dict(expected, passed=1),
                        dict(expected, count=3.0), dict(expected, mode="constant"),
                        dict(expected, error="failure"), dict(expected, extra=0),
                        dict(expected, windows=[]),
                        dict(expected, windows=[{"p_mw": float("nan")}])):
            with self.assertRaises(AssertionError):
                self.assert_analysis_equal(changed, expected)

    def test_integrated_capture_preserves_rms_settings_and_readback_scope(self):
        supplied = json.loads((EVIDENCE / "FT-36_integrated_rms_zip_creation_lab_pc.json")
                              .read_text(encoding="utf-8"))
        responses = {key: json.loads(value) for key, value in supplied["raw_response_text"].items()}
        self.assertEqual(len(responses), 11)
        preview, creation = responses["preview"], responses["creation"]
        self.assertTrue(preview["success"])
        self.assertFalse(preview["applied"])
        self.assertTrue(creation["success"])
        self.assertTrue(creation["applied"])
        self.assertTrue(creation["type_created"])
        self.assertTrue(creation["load_created"])
        self.assertEqual(preview["confirmation_required"], creation["confirmation_required"])
        self.assertEqual(creation["load_model"], "zip_rms")
        typ = responses["type_readback"]["results"][0]
        load = responses["load_readback"]["results"][0]
        self.assertEqual(responses["type_readback"]["total_count"], 1)
        self.assertEqual(responses["load_readback"]["total_count"], 1)
        self.assertEqual(typ["full_name"], creation["created_type"])
        self.assertEqual(load["full_name"], creation["created_load"])
        for key, value in creation["retained_type_attributes"].items():
            self.assertEqual(typ["values"][key], value)
        for key, value in creation["retained_derived_attributes"].items():
            self.assertEqual(typ["values"][key], value)
        self.assertEqual(typ["values"]["loddy"], 100)
        self.assertEqual(typ["values"]["i_nln"], 1)
        self.assertEqual(load["values"]["outserv"], 1)
        self.assertLess(load["values"]["qlini"], 0)
        self.assertEqual(responses["grid_preflight"]["results"][0]["values"]["frnom"], 50)
        self.assertEqual(responses["grid_frequency_reread"]["results"][0]["values"]["frnom"], 50)

    def test_complete_traces_reproduce_all_settled_window_findings(self):
        report = json.loads((EVIDENCE / "FT-35_zip_rms_diagnostic_lab_pc.json")
                            .read_text(encoding="utf-8"))
        self.assertTrue(report["success"])
        self.assertFalse(report["creator_rms_zip_validated"])
        self.assertEqual([run["mode"] for run in report["runs"]], list(probe.MODES))
        for run in report["runs"]:
            self.assertTrue(run["restored"])
            self.assertTrue(run["cleanup_ok"])
            self.assertEqual(run["remaining_objects"], [])
            self.assertEqual(len(run["trace"]), 503)
            self.assert_analysis_equal(probe.analyze(run["trace"], run["retained_type"],
                                                   run["mode"], run["loadflow"]), run["analysis"])
        creator, nonlinear, constant = report["runs"]
        self.assertFalse(creator["analysis"]["matches_zip"])
        self.assertTrue(creator["analysis"]["matches_initial_constant_impedance"])
        self.assertTrue(nonlinear["analysis"]["control_passed"])
        self.assertTrue(constant["analysis"]["control_passed"])

    def test_uses_lab_verified_tstart_not_unsupported_start(self):
        tree = ast.parse(inspect.getsource(probe.validate_case))
        configs = [call.args[1] for call in ast.walk(tree)
                   if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                   and call.func.id == "set_values" and len(call.args) == 2
                   and isinstance(call.args[0], ast.Name) and call.args[0].id == "inc"]
        self.assertEqual(len(configs), 1)
        values = {key.value: value for key, value in zip(configs[0].keys, configs[0].values)}
        self.assertNotIn("start", values)
        self.assertEqual(ast.literal_eval(values["tstart"]), 0.)

    def test_failed_setup_does_not_run_later_cases(self):
        failed = dict(success=False, restored=False, cleanup_ok=False,
                      remaining_objects=["temporary grid"])
        with patch.object(probe, "validate_case", return_value=failed) as call:
            report = probe.validate(None)
        call.assert_called_once_with(None, "creator_unchanged")
        self.assertFalse(report["success"])
        self.assertFalse(report["creator_rms_zip_validated"])
        self.assertEqual(report["remaining_objects"], ["temporary grid"])

    def test_settled_mismatch_keeps_other_control_but_not_success(self):
        runs = [dict(mode=mode, success=(mode != "nonlinear_zip"), restored=True,
                     cleanup_ok=True, remaining_objects=[],
                     analysis=dict(experiment_valid=True, matches_zip=False)) for mode in probe.MODES]
        with patch.object(probe, "validate_case", side_effect=runs) as call:
            report = probe.validate(None)
        self.assertEqual(call.call_count, 3)
        self.assertFalse(report["success"])
        self.assertFalse(report["creator_rms_zip_validated"])

    def test_successful_controls_do_not_validate_creator_defaults(self):
        runs = [dict(mode=mode, success=True, restored=True, cleanup_ok=True,
                     remaining_objects=[], analysis=dict(matches_zip=False)) for mode in probe.MODES]
        with patch.object(probe, "validate_case", side_effect=runs):
            report = probe.validate(None)
        self.assertTrue(report["success"])
        self.assertFalse(report["creator_rms_zip_validated"])

    def test_complete_export_never_overwrites_a_previous_run(self):
        report = dict(success=False, error="Diagnostic failure", trace=["x" * 25000])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            with patch.object(probe, "validate", return_value=report) as call:
                probe.run_and_save(None, path)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)
                with self.assertRaises(FileExistsError):
                    probe.run_and_save(None, path)
                self.assertEqual(call.call_count, 1)

    def test_unwritable_output_stops_before_any_simulation(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(probe, "validate") as call:
                with self.assertRaises(OSError):
                    probe.run_and_save(None, Path(folder) / "missing" / "result.json")
                call.assert_not_called()
