from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.core import (
    _Job,
    _jobs,
    build_run_command,
    hope_cancel_job,
    hope_case_info,
    hope_debug_solver_environment,
    hope_debug_solver_environment_async,
    hope_job_status,
    hope_output_summary,
    hope_run_hope,
    julia_string_literal,
    setup_command,
)
from hope_mcp_server.server import create_mcp_server


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
        self.assertIn(result["solver"], {"cbc", "clp", "highs", "scip", "gurobi", "cplex"})
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
        self.assertIn("md_gtep_clean", result["allowed_case_ids"])
        self.assertIn("MD_GTEP_clean_case", result["allowed_case_ids"])
        self.assertIn("USA_64zone_GTEP_case", result["allowed_case_ids"])

    def test_case_info_accepts_modelcases_directory_name(self) -> None:
        result = hope_case_info("MD_GTEP_clean_case")
        self.assertTrue(result["ok"])
        self.assertEqual(result["model_mode"], "GTEP")

    def test_case_info_accepts_modelcases_prefixed_path(self) -> None:
        result = hope_case_info("ModelCases/MD_GTEP_clean_case")
        self.assertTrue(result["ok"])
        canonical = hope_case_info("MD_GTEP_clean_case")
        self.assertTrue(canonical["ok"])
        self.assertEqual(result["solver"], canonical["solver"])

    def test_read_only_server_exposes_only_fetch_tools(self) -> None:
        mcp = create_mcp_server(read_only=True, host="127.0.0.1", port=8765)
        tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}
        self.assertIn("hope_case_info", tool_names)
        self.assertIn("hope_read_output", tool_names)
        self.assertNotIn("hope_run_hope", tool_names)
        self.assertNotIn("hope_update_settings", tool_names)
        self.assertNotIn("hope_open_dashboard", tool_names)
        self.assertNotIn("hope_cancel_job", tool_names)
        self.assertNotIn("hope_debug_solver_environment", tool_names)
        self.assertNotIn("hope_debug_solver_environment_async", tool_names)

    def test_full_server_keeps_run_tools_for_claude(self) -> None:
        mcp = create_mcp_server(read_only=False, host="127.0.0.1", port=8766)
        tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}
        self.assertIn("hope_run_hope", tool_names)
        self.assertIn("hope_update_settings", tool_names)
        self.assertIn("hope_job_status", tool_names)
        self.assertIn("hope_cancel_job", tool_names)
        self.assertIn("hope_debug_solver_environment", tool_names)
        self.assertIn("hope_debug_solver_environment_async", tool_names)

    def test_read_only_server_accepts_configured_public_hostname(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {"HOPE_MCP_PUBLIC_HOSTNAME": "hope.hope-mcp.com"},
            clear=False,
        ):
            mcp = create_mcp_server(read_only=True, host="127.0.0.1", port=8767)
        settings = mcp.settings.transport_security
        self.assertIsNotNone(settings)
        self.assertIn("hope.hope-mcp.com", settings.allowed_hosts)
        self.assertIn("https://hope.hope-mcp.com", settings.allowed_origins)

    def test_build_run_command_uses_env_config(self) -> None:
        case_path = REPO_ROOT / "ModelCases" / "MD_GTEP_clean_case"
        command = build_run_command(REPO_ROOT, JULIA_BIN, case_path)
        self.assertEqual(
            command,
            [
                JULIA_BIN,
                "--startup-file=no",
                f"--project={REPO_ROOT}",
                "-e",
                f"using HOPE; HOPE.run_hope({julia_string_literal(case_path)})",
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
        process = mock.Mock()
        process.poll.return_value = 1
        job = _Job(
            job_id="depsfail",
            command=[],
            process=process,
            stdout_lines=[],
            stderr_lines=[
                "ArgumentError: Package JuMP is required but does not seem to be installed:",
                " - Run `Pkg.instantiate()` to install all recorded dependencies.",
            ],
        )
        _jobs[job.job_id] = job
        self.addCleanup(lambda: _jobs.pop(job.job_id, None))

        result = hope_job_status(job.job_id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "hope_environment_not_instantiated")
        self.assertEqual(
            result["setup_command"],
            setup_command(REPO_ROOT, JULIA_BIN),
        )

    def test_cancel_job_returns_not_found_for_unknown_id(self) -> None:
        result = hope_cancel_job("missing-job")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "job_not_found")

    def test_cancel_job_terminates_running_process_and_status_turns_cancelled(self) -> None:
        process = mock.Mock()
        process.poll.side_effect = [None, -15, -15]
        process.wait.return_value = -15
        job = _Job(
            job_id="cancelme",
            command=["julia"],
            process=process,
            stdout_lines=["starting", "working"],
            stderr_lines=["received interrupt"],
        )
        _jobs[job.job_id] = job
        self.addCleanup(lambda: _jobs.pop(job.job_id, None))

        result = hope_cancel_job(job.job_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(result["forced_kill"])
        process.terminate.assert_called_once()
        process.kill.assert_not_called()

        status = hope_job_status(job.job_id)
        self.assertTrue(status["ok"])
        self.assertEqual(status["status"], "cancelled")
        self.assertEqual(status["stderr"], "received interrupt")

    def test_cancel_job_force_kills_when_terminate_times_out(self) -> None:
        process = mock.Mock()
        process.poll.side_effect = [None, -9]
        process.wait.side_effect = [subprocess.TimeoutExpired(cmd=["julia"], timeout=5.0), -9]
        job = _Job(
            job_id="forcekill",
            command=["julia"],
            process=process,
        )
        _jobs[job.job_id] = job
        self.addCleanup(lambda: _jobs.pop(job.job_id, None))

        result = hope_cancel_job(job.job_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "cancelled")
        self.assertTrue(result["forced_kill"])
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_debug_solver_environment_reports_probe_details(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["julia"],
            returncode=0,
            stdout=(
                "STEP=julia_start\n"
                "ACTIVE_PROJECT=E:/repo/Project.toml\n"
                "DEPOT_PATH=E:/julia_depot\n"
                "HOPE_PATH=E:/repo/src/HOPE.jl\n"
                "OPTIMIZER_CONSTRUCTOR_VALUE=Gurobi.Optimizer\n"
                "MODEL_TYPE=Model\n"
                "PROBE_STATUS=ok\n"
            ),
            stderr="",
        )
        with (
            mock.patch("hope_mcp_server.core.validate_julia_command", return_value=(JULIA_BIN, None)),
            mock.patch("hope_mcp_server.core.subprocess.run", return_value=completed) as run_mock,
        ):
            result = hope_debug_solver_environment(case_id="MD_GTEP_clean_case", solver="gurobi")
        self.assertTrue(result["ok"])
        self.assertEqual(result["solver"], "gurobi")
        self.assertEqual(result["probe"]["OPTIMIZER_CONSTRUCTOR_VALUE"], "Gurobi.Optimizer")
        self.assertEqual(result["probe"]["PROBE_STATUS"], "ok")
        run_mock.assert_called_once()

    def test_debug_solver_environment_reports_timeout_progress(self) -> None:
        timeout_error = subprocess.TimeoutExpired(
            cmd=["julia"],
            timeout=120.0,
            output="STEP=julia_start\nSTEP=using_HOPE_start\n",
            stderr="",
        )
        with (
            mock.patch("hope_mcp_server.core.validate_julia_command", return_value=(JULIA_BIN, None)),
            mock.patch("hope_mcp_server.core.subprocess.run", side_effect=timeout_error),
        ):
            result = hope_debug_solver_environment(case_id="MD_GTEP_clean_case", solver="gurobi")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "debug_probe_timeout")
        self.assertEqual(result["parsed_stdout"]["STEP"], "using_HOPE_start")

    def test_debug_solver_environment_async_launches_background_job(self) -> None:
        with (
            mock.patch("hope_mcp_server.core.validate_julia_command", return_value=(JULIA_BIN, None)),
            mock.patch("hope_mcp_server.core._launch_job", return_value="probe123") as launch_mock,
        ):
            result = hope_debug_solver_environment_async(
                case_id="MD_GTEP_clean_case",
                solver="gurobi",
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["job_id"], "probe123")
        self.assertEqual(result["solver"], "gurobi")
        self.assertIn("--startup-file=no", result["command"])
        launch_mock.assert_called_once()

    def test_setup_command_disables_startup_file(self) -> None:
        command = setup_command(REPO_ROOT, JULIA_BIN)
        self.assertIn("--startup-file=no", command)

    def test_job_status_returns_parsed_probe_for_completed_debug_job(self) -> None:
        process = mock.Mock()
        process.poll.return_value = 0
        job = _Job(
            job_id="debugdone",
            command=["julia"],
            process=process,
            job_kind="debug_probe",
            stdout_lines=[
                "STEP=julia_start",
                "OPTIMIZER_CONSTRUCTOR_VALUE=HiGHS.Optimizer",
                "PROBE_STATUS=ok",
            ],
        )
        _jobs[job.job_id] = job
        self.addCleanup(lambda: _jobs.pop(job.job_id, None))

        result = hope_job_status(job.job_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["probe"]["OPTIMIZER_CONSTRUCTOR_VALUE"], "HiGHS.Optimizer")
        self.assertEqual(result["probe"]["PROBE_STATUS"], "ok")
        self.assertNotIn("output_summary", result)


if __name__ == "__main__":
    unittest.main()
