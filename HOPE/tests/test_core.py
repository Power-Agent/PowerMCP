from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.core import (
    build_run_command,
    hope_case_info,
    hope_output_summary,
    hope_run_hope,
    setup_command,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
JULIA_BIN = (
    "/Users/qianzhang/.julia/juliaup/julia-1.11.6+0.aarch64.apple.darwin14/bin/julia"
)


class HopeCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "HOPE_REPO_ROOT": str(REPO_ROOT),
                "HOPE_JULIA_BIN": JULIA_BIN,
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()

    def test_case_info_reads_yaml_and_output_inventory(self) -> None:
        result = hope_case_info()
        self.assertTrue(result["ok"])
        self.assertEqual(result["case_id"], "md_gtep_clean")
        self.assertEqual(result["model_mode"], "GTEP")
        self.assertEqual(result["solver"], "cbc")
        self.assertEqual(result["DataCase"], "Data_100RPS/")
        self.assertTrue(result["output_exists"])
        self.assertIn("capacity.csv", result["output_csv_files"])
        self.assertGreater(result["output_csv_count"], 0)

    def test_output_summary_reports_system_cost_and_solar_builds(self) -> None:
        result = hope_output_summary()
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["total_system_cost"])
        self.assertGreater(result["total_system_cost"], 0.0)
        solar_builds = [
            build
            for build in result["new_generation_builds"]
            if build["technology"] == "SolarPV"
        ]
        self.assertTrue(solar_builds)
        self.assertIn("system_cost.csv", result["available_output_files"])

    def test_invalid_case_id_returns_allowed_values_error(self) -> None:
        result = hope_case_info("not_a_case")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "invalid_case_id")
        self.assertEqual(result["allowed_case_ids"], ["md_gtep_clean"])

    def test_build_run_command_uses_env_config(self) -> None:
        case_path = REPO_ROOT / "ModelCases" / "MD_GTEP_clean_case"
        command = build_run_command(REPO_ROOT, JULIA_BIN, case_path)
        self.assertEqual(
            command,
            [
                JULIA_BIN,
                f"--project={REPO_ROOT}",
                str(REPO_ROOT / "src" / "main.jl"),
                str(case_path),
            ],
        )

    def test_missing_julia_path_returns_structured_error(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {
                "HOPE_REPO_ROOT": str(REPO_ROOT),
                "HOPE_JULIA_BIN": str(PACKAGE_ROOT / "missing-julia"),
            },
            clear=False,
        ):
            result = hope_run_hope()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "julia_not_found")
        self.assertIn("setup_command", result)

    def test_dependency_failure_returns_setup_command(self) -> None:
        completed = mock.Mock(
            returncode=1,
            stdout="",
            stderr=(
                "ArgumentError: Package JuMP is required but does not seem to be installed:\n"
                " - Run `Pkg.instantiate()` to install all recorded dependencies."
            ),
        )
        with mock.patch("hope_mcp_server.core.subprocess.run", return_value=completed):
            result = hope_run_hope()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "hope_environment_not_instantiated")
        self.assertEqual(
            result["setup_command"],
            setup_command(REPO_ROOT, JULIA_BIN),
        )


if __name__ == "__main__":
    unittest.main()
