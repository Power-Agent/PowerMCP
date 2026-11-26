"""Offline checks only: no PowerFactory engine is imported or executed."""

import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"
SPEC = importlib.util.spec_from_file_location(
    "earth_fault_reference_probe",
    EVIDENCE / "scripts" / "lab_transformer_earth_fault_reference_check.py",
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ReferenceEvidenceTest(unittest.TestCase):
    def test_simple_reactance_only_hand_reference(self):
        result = probe.reference_currents(100, 100, 1000, 0, 0, .1, 0, .1)
        ibase = 1 / math.sqrt(3)
        self.assertAlmostEqual(result["three_phase_ka"], ibase / .2)
        self.assertAlmostEqual(result["earth_fault_ka"], 3 * ibase / .5)
        self.assertEqual(result["hv_impedance_base_ohm"], 100)

    def test_neutral_impedance_uses_factor_three(self):
        result = probe.reference_currents(20, 110, 1000, .1, .01, .1, .02, .1,
                                          rn_ohm=20, xn_ohm=5)
        self.assertAlmostEqual(result["Z0_pu"]["real"], .02 + 60 / 605)
        self.assertAlmostEqual(result["Z0_pu"]["imag"], .1 + 15 / 605)

    def test_saved_result_is_complete_and_reproducible(self):
        record = json.loads((EVIDENCE / "FT-32_transformer_earth_fault_reference_lab_pc.json")
                            .read_text(encoding="utf-8"))
        self.assertTrue(record["success"])
        self.assertTrue(record["restored"])
        self.assertTrue(record["cleanup_ok"])
        self.assertEqual(record["remaining_objects"], [])
        self.assertTrue(record["method_template_unchanged"])
        self.assertTrue(record["source_only_control"]["passed"])
        self.assertEqual([r["label"] for r in record["rows"]],
                         ["baseline", "higher_R0", "higher_X0", "neutral_resistance"])
        typ, source = record["original_type"], record["source_inputs"]
        for row in record["rows"]:
            expected = probe.reference_currents(
                typ["strn"], typ["utrn_h"], source["snss"], source["rntxn"],
                typ["r1pu"], typ["x1pu"], row["retained_r0pu"],
                row["retained_x0pu"], row["neutral_resistance_ohm"])
            for key in ("three_phase_ka", "earth_fault_ka", "hv_terminal_I0_ka"):
                self.assertAlmostEqual(expected[key], row["reference"][key], places=12)
            self.assertTrue(probe.compare_reference(dict(row), expected))
            self.assertTrue(row["passed"])
            self.assertTrue(row["absolute_reference_passed"])

    def test_absolute_mismatch_is_not_hidden(self):
        reference = dict(three_phase_ka=1., earth_fault_ka=.9,
                         hv_terminal_I0_ka=.3, lv_terminal_I0_ka=0.)
        row = dict(reference, earth_fault_ka=1.1)
        self.assertFalse(probe.compare_reference(row, reference))
        self.assertFalse(row["absolute_reference_passed"])

    def test_invalid_input_is_rejected(self):
        for sk in (0, -1, math.nan, math.inf):
            with self.assertRaises(ValueError):
                probe.reference_currents(20, 110, sk, .1, .01, .1, .01, .1)

    def test_export_preserves_long_json_without_overwrite(self):
        result = {"success": True, "payload": "x" * 25000, "label": "Prüfung",
                  "restored": True, "cleanup_ok": True, "remaining_objects": []}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result.json"
            with patch.object(probe, "validate", return_value=result) as validate:
                self.assertEqual(probe.run_and_save(None, target), result)
                self.assertEqual(json.loads(target.read_text(encoding="utf-8")), result)
                with self.assertRaises(FileExistsError):
                    probe.run_and_save(None, target)
                self.assertEqual(validate.call_count, 1)

    def test_missing_destination_stops_before_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(probe, "validate") as validate:
                with self.assertRaises(OSError):
                    probe.run_and_save(None, Path(folder) / "missing" / "result.json")
                validate.assert_not_called()

    def test_validation_exception_is_exported(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "result.json"
            with patch.object(probe, "validate", side_effect=RuntimeError("Wrong project")):
                probe.run_and_save(None, target)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "Wrong project")
