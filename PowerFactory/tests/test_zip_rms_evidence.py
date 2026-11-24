"""Offline FT-35 reproducibility checks; never import a licensed PF engine."""

import ast
import importlib.util
import inspect
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"
SPEC = importlib.util.spec_from_file_location(
    "zip_rms_diagnostic", EVIDENCE / "scripts" / "lab_zip_rms_diagnostic.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class RmsZipEvidenceTest(unittest.TestCase):
    def load_e2e(self):
        modules = []
        for label, filename in (("ft38_helper", "lab_zip_rms_multiseed_check.py"),
                                ("ft38_e2e", "lab_zip_rms_e2e_check.py")):
            spec = importlib.util.spec_from_file_location(label, EVIDENCE / "scripts" / filename)
            module = importlib.util.module_from_spec(spec)
            with patch.dict(sys.modules, {"lab_zip_rms_multiseed_check": modules[0]} if modules else {}):
                spec.loader.exec_module(module)
            modules.append(module)
        return modules[1]

    def test_e2e_capture_state_and_actual_created_traces(self):
        e2e = self.load_e2e()
        report = json.loads((EVIDENCE / "FT-38_zip_rms_e2e_lab_pc.json").read_text(encoding="utf-8"))
        capture = json.loads((EVIDENCE / "FT-38_zip_rms_e2e_capture_lab_pc.json").read_text(encoding="utf-8"))
        state = json.loads((EVIDENCE / "FT-38_zip_rms_e2e_state_lab_pc.json").read_text(encoding="utf-8"))
        self.assertEqual(capture, report["capture"])
        self.assertEqual(json.loads(report["capture_text"]), capture)
        # Historical original-byte hash, not a hash of the sanitized archive.
        self.assertEqual(report["capture_sha256"],
                         "9a0846cf7b3b0444f70cc9d0f6b4f1eac6058eb49b6ddeccf86fb6bae5c44414")
        self.assertTrue(state["closed"])
        self.assertTrue(state["ready"])
        self.assertTrue(state["result_file"].endswith("ZIP_RMS_E2E_20261031T163348Z_1997c5f1.json"))
        self.assertEqual({k: v for k, v in state.items() if k not in ("closed", "result_file")},
                         {k: v for k, v in report["state"].items() if k not in ("closed", "result_file")})
        for flag in ("success", "restored", "cleanup_ok"):
            self.assertTrue(report[flag])
        self.assertEqual(report["remaining_objects"], [])
        self.assertEqual(report["cleanup_errors"], [])
        self.assertNotIn("error", report)
        e2e.check_capture(report["state"], capture)
        self.assertEqual([r["seed"] for r in report["runs"]], [0, 4])
        for run in report["runs"]:
            with self.subTest(seed=run["seed"]):
                creation = capture[str(run["seed"])]["creation"]
                self.assertEqual(run["created_load"], creation["created_load"])
                self.assertEqual(run["created_type"], creation["created_type"])
                self.assertTrue(run["success"])
                self.assertTrue(run["created_type_unchanged"])
                self.assertTrue(run["returned_out_of_service"])
                self.assertNotIn("error", run)
                self.assertEqual(len(run["trace"]), 503)
                self.assertTrue(all(math.isfinite(v) for s in run["trace"] for v in s.values()))
                self.assertEqual(run["q0_mvar"] > 0, run["seed"] == 0)
                for key, value in creation["item"]["powerfactory_attributes"].items():
                    self.assertEqual(run[{"plini": "p0_mw", "qlini": "q0_mvar"}[key]], value)
                for key, expected in {**creation["item"]["type_attributes"],
                                      **creation["item"]["derived_type_attributes"]}.items():
                    e2e.h.check(run["retained_type"][key], expected, key)
                activation = run["case_activation"]
                self.assertFalse(activation["activation_needed"])
                self.assertEqual(activation["before"], state["case"])
                self.assertEqual(activation["after"], state["case"])
                self.assertEqual(activation["target"], state["case"])
                analysis = e2e.h.analyze(run["trace"], run["retained_type"], "nonlinear_zip",
                                         run["loadflow"], run["p0_mw"], run["q0_mvar"])
                self.assert_analysis_equal(analysis, run["analysis"])
                self.assertTrue(analysis["control_passed"])
                self.assertFalse(analysis["matches_constant_power"])
                self.assertFalse(analysis["matches_initial_constant_impedance"])

    def test_e2e_rejects_changed_capture_and_capacitive_response(self):
        e2e = self.load_e2e()
        report = json.loads((EVIDENCE / "FT-38_zip_rms_e2e_lab_pc.json").read_text(encoding="utf-8"))
        capture = report["capture"]
        capture["0"]["creation"]["confirmation_required"] = "incorrect token"
        with self.assertRaisesRegex(RuntimeError, "Confirmation changed"):
            e2e.check_capture(report["state"], capture)
        run = report["runs"][1]
        for sample in run["trace"]:
            if 1 <= sample["time_s"] < 3:
                sample["q_mvar"] *= 1.1
        analysis = e2e.h.analyze(run["trace"], run["retained_type"], "nonlinear_zip",
                                 run["loadflow"], run["p0_mw"], run["q0_mvar"])
        self.assertFalse(analysis["control_passed"])

    def test_e2e_active_case_skips_redundant_activation_on_both_runs(self):
        e2e = self.load_e2e()
        app, case = MagicMock(), MagicMock()
        case.GetFullName.return_value = "temporary.IntCase"
        case.Activate.return_value = 1
        app.GetActiveStudyCase.return_value = case
        app.GetActiveScenario.return_value = None
        with patch.object(e2e.h, "active_grids", return_value=["temporary.ElmNet"]) as grids:
            for _ in range(2):
                self.assertFalse(e2e.activate_case(app, case, "temporary.ElmNet")["activation_needed"])
        case.Activate.assert_not_called()
        self.assertEqual(grids.call_count, 2)

    def test_e2e_required_activation_is_verified_and_failures_still_rejected(self):
        e2e = self.load_e2e()
        app, case, other = MagicMock(), MagicMock(), MagicMock()
        case.GetFullName.return_value = "temporary.IntCase"
        other.GetFullName.return_value = "other.IntCase"
        app.GetActiveStudyCase.side_effect = [other, case]
        case.Activate.return_value = 0
        self.assertTrue(e2e.activate_case(app, case)["activation_needed"])
        case.Activate.assert_called_once_with()
        app.GetActiveStudyCase.side_effect = None
        app.GetActiveStudyCase.return_value = other
        with self.assertRaisesRegex(RuntimeError, "activation mismatch"):
            e2e.activate_case(app, case)
        case.Activate.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "Activate returned 1"):
            e2e.activate_case(app, case)

    def test_e2e_matching_case_does_not_bypass_grid_or_scenario_isolation(self):
        e2e = self.load_e2e()
        app, case = MagicMock(), MagicMock()
        case.GetFullName.return_value = "temporary.IntCase"
        app.GetActiveStudyCase.return_value = case
        app.GetActiveScenario.return_value = None
        with patch.object(e2e.h, "active_grids", return_value=["temporary.ElmNet", "production.ElmNet"]):
            with self.assertRaisesRegex(RuntimeError, "isolation failed"):
                e2e.activate_case(app, case, "temporary.ElmNet")
        app.GetActiveScenario.return_value = MagicMock()
        with patch.object(e2e.h, "active_grids", return_value=["temporary.ElmNet"]):
            with self.assertRaisesRegex(RuntimeError, "isolation failed"):
                e2e.activate_case(app, case, "temporary.ElmNet")
        case.Activate.assert_not_called()

    def test_multiseed_traces_reproduce_all_twelve_analyses(self):
        spec = importlib.util.spec_from_file_location(
            "zip_rms_multiseed", EVIDENCE / "scripts/lab_zip_rms_multiseed_check.py")
        multi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(multi)
        report = json.loads((EVIDENCE / "FT-37_zip_rms_multiseed_lab_pc.json").read_text(encoding="utf-8"))
        self.assertTrue(report["success"])
        self.assertTrue(report["restored"])
        self.assertTrue(report["cleanup_ok"])
        self.assertEqual(report["remaining_objects"], [])
        plans, _ = multi.sampled_plans(EVIDENCE.parents[1])
        self.assertEqual(report["selected_seeds"], [0, 1, 2, 4, 7, 15])
        self.assertEqual(len(report["runs"]), 12)
        self.assertEqual([r["seed"] for r in report["runs"]],
                         [p["seed"] for p in plans for _ in range(2)])
        for index, run in enumerate(report["runs"]):
            with self.subTest(seed=run["seed"], mode=run["mode"]):
                self.assertEqual(run["mode"], ("nonlinear_zip", "constant_power_control")[index % 2])
                # Historical evidence keeps its original validation prose.
                recorded, current = dict(run["sampled_plan"]), dict(plans[index // 2])
                for plan in (recorded, current):
                    plan.pop("limitations")
                    plan["rms_configuration"] = dict(plan["rms_configuration"])
                    for field in ("validation", "limitations"):
                        plan["rms_configuration"].pop(field)
                self.assertEqual(recorded, current)
                self.assertTrue(run["success"])
                self.assertTrue(run["restored"])
                self.assertTrue(run["cleanup_ok"])
                self.assertEqual(run["remaining_objects"], [])
                self.assertNotIn("error", run)
                self.assertEqual(run["nominal_frequency_hz"], 50)
                self.assertEqual(len(run["trace"]), 503)
                self.assertTrue(all(math.isfinite(v) for s in run["trace"] for v in s.values()))
                self.assertGreater(run["p0_mw"], 0)
                self.assertEqual(run["q0_mvar"] > 0, run["seed"] in (0, 1, 2))
                analysis = multi.analyze(run["trace"], run["retained_type"], run["mode"],
                                         run["loadflow"], run["p0_mw"], run["q0_mvar"])
                self.assert_analysis_equal(analysis, run["analysis"])
                self.assertTrue(analysis["control_passed"])
                self.assertTrue(analysis["matches_zip"])
                self.assertEqual(analysis["matches_constant_power"], run["mode"] == "constant_power_control")
                self.assertFalse(analysis["matches_initial_constant_impedance"])

    def test_multiseed_analysis_rejects_changed_capacitive_trace(self):
        spec = importlib.util.spec_from_file_location(
            "zip_rms_multiseed", EVIDENCE / "scripts/lab_zip_rms_multiseed_check.py")
        multi = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(multi)
        report = json.loads((EVIDENCE / "FT-37_zip_rms_multiseed_lab_pc.json").read_text(encoding="utf-8"))
        run = next(r for r in report["runs"] if r["seed"] == 7 and r["mode"] == "nonlinear_zip")
        for sample in run["trace"]:
            if 1 <= sample["time_s"] < 3:
                sample["q_mvar"] *= 1.1
        analysis = multi.analyze(run["trace"], run["retained_type"], run["mode"],
                                 run["loadflow"], run["p0_mw"], run["q0_mvar"])
        self.assertFalse(analysis["control_passed"])
        self.assertFalse(analysis["matches_zip"])

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
