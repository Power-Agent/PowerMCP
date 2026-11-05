from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.core import (  # noqa: E402
    _holistic_request_jobs,
    _Job,
    _jobs,
    hope_holistic_status,
    hope_run_holistic,
)


class HolisticStateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runs = self.root / "agent-runs"
        runner = self.root / "tools" / "repo_utils" / "run_holistic_agent_job.jl"
        runner.parent.mkdir(parents=True)
        runner.write_text("# test runner\n", encoding="utf-8")
        self.runner = runner
        self.gtep = self._write_case("gtep_case", "GTEP")
        self.pcm = self._write_case("pcm_case", "PCM")
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "HOPE_REPO_ROOT": str(self.root),
                "HOPE_MODELCASES_PATH": str(self.root / "ModelCases"),
                "HOPE_AGENT_RUNS_ROOT": str(self.runs),
                "HOPE_JULIA_BIN": "julia-test",
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        for request_id in list(_holistic_request_jobs):
            if request_id.startswith("state-"):
                _holistic_request_jobs.pop(request_id, None)
        for job_id, job in list(_jobs.items()):
            if job.request_id.startswith("state-"):
                _jobs.pop(job_id, None)
        self.temporary.cleanup()

    def _write_case(self, name: str, mode: str) -> Path:
        case = self.root / "ModelCases" / name
        (case / "Settings").mkdir(parents=True)
        (case / "Data").mkdir()
        (case / "Settings" / "HOPE_model_settings.yml").write_text(
            f"model_mode: {mode}\nsolver: highs\nDataCase: Data/\n",
            encoding="utf-8",
        )
        (case / "Data" / "input.csv").write_text("name,value\ntest,1\n", encoding="utf-8")
        return case

    def _fake_launch(self, command: list[str], repo_root: Path, case_id: str = "", **kwargs: object) -> str:
        process = mock.Mock()
        process.pid = os.getpid()
        process.poll.return_value = None
        _jobs["statejob"] = _Job(
            job_id="statejob",
            command=command,
            process=process,
            case_id=case_id,
            job_kind=str(kwargs.get("job_kind", "generic")),
            request_id=str(kwargs.get("request_id", "")),
            workspace_path=str(kwargs.get("workspace_path", "")),
            manifest_path=str(kwargs.get("manifest_path", "")),
            output_case_path=str(kwargs.get("output_case_path", "")),
        )
        return "statejob"

    def _launch(self, request_id: str) -> dict:
        with (
            mock.patch(
                "hope_mcp_server.core.validate_julia_command",
                return_value=("julia-test", None),
            ),
            mock.patch(
                "hope_mcp_server.core._launch_job",
                side_effect=self._fake_launch,
            ),
        ):
            return hope_run_holistic(
                "gtep_case",
                "pcm_case",
                request_id=request_id,
                solver="highs",
            )

    def test_launch_records_process_identity_and_reconnect_reports_running(self) -> None:
        launched = self._launch("state-running")
        manifest = yaml.safe_load(Path(launched["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["launcher_pid"], os.getpid())
        self.assertEqual(manifest["process_pid"], os.getpid())

        _holistic_request_jobs.pop("state-running", None)
        with mock.patch("hope_mcp_server.core._process_is_alive", return_value=True):
            recovered = hope_holistic_status("state-running")
        self.assertTrue(recovered["ok"])
        self.assertEqual(recovered["status"], "running")

    def test_dead_process_becomes_durable_failure(self) -> None:
        self._launch("state-dead")
        _holistic_request_jobs.pop("state-dead", None)
        with mock.patch("hope_mcp_server.core._process_is_alive", return_value=False):
            failed = hope_holistic_status("state-dead")
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error_type"], "job_failed")
        self.assertIn("no longer running", failed["message"])

        persisted = hope_holistic_status("state-dead")
        self.assertFalse(persisted["ok"])
        self.assertEqual(persisted["status"], "failed")

    def test_dead_launcher_during_preparation_becomes_failure(self) -> None:
        launched = self._launch("state-preparing")
        manifest_path = Path(launched["manifest_path"])
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "VALIDATED"
        manifest.pop("process_pid", None)
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        _holistic_request_jobs.pop("state-preparing", None)

        with mock.patch("hope_mcp_server.core._process_is_alive", return_value=False):
            failed = hope_holistic_status("state-preparing")
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["status"], "failed")
        self.assertIn("preparing", failed["message"])

    def test_terminal_status_is_stable_across_reconnect(self) -> None:
        self._launch("state-done")
        job = _jobs["statejob"]
        job.process.poll.return_value = 0
        job.stdout_lines = [
            "HOPE_HANDOFF_VALID=true",
            "HOPE_TRANSFER_VALID=true",
        ]
        current = hope_holistic_status("state-done")
        self.assertTrue(current["ok"])
        self.assertEqual(current["status"], "done")

        _holistic_request_jobs.pop("state-done", None)
        recovered = hope_holistic_status("state-done")
        self.assertTrue(recovered["ok"])
        self.assertEqual(recovered["status"], "done")

    def test_failed_status_is_stable_across_reconnect(self) -> None:
        self._launch("state-failed")
        job = _jobs["statejob"]
        job.process.poll.return_value = 2
        job.stderr_lines = ["solver failed"]
        current = hope_holistic_status("state-failed")
        self.assertFalse(current["ok"])
        self.assertEqual(current["error_type"], "job_failed")
        self.assertEqual(current["status"], "failed")

        _holistic_request_jobs.pop("state-failed", None)
        recovered = hope_holistic_status("state-failed")
        self.assertFalse(recovered["ok"])
        self.assertEqual(recovered["error_type"], "job_failed")
        self.assertEqual(recovered["status"], "failed")

    def test_corrupt_active_manifest_returns_structured_error(self) -> None:
        launched = self._launch("state-corrupt")
        Path(launched["manifest_path"]).write_text("- not\n- a\n- mapping\n", encoding="utf-8")
        _jobs["statejob"].process.poll.return_value = 0
        result = hope_holistic_status("state-corrupt")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "invalid_holistic_manifest")
        self.assertEqual(result["status"], "failed")

    def test_invalid_case_yaml_returns_structured_error(self) -> None:
        (self.gtep / "Settings" / "HOPE_model_settings.yml").write_text(
            "model_mode: [GTEP\n",
            encoding="utf-8",
        )
        result = hope_run_holistic(
            "gtep_case",
            "pcm_case",
            request_id="state-invalid-yaml",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "invalid_holistic_inputs")

    def test_missing_runner_fails_before_workspace_creation(self) -> None:
        self.runner.unlink()
        with mock.patch("hope_mcp_server.core.validate_julia_command") as validate:
            result = hope_run_holistic(
                "gtep_case",
                "pcm_case",
                request_id="state-old-hope",
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "incompatible_hope_checkout")
        self.assertEqual(result["minimum_hope_revision"], "8126f0f")
        self.assertFalse((self.runs / "state-old-hope").exists())
        validate.assert_not_called()

    def test_equivalent_case_identifiers_are_idempotent(self) -> None:
        first = self._launch("state-canonical")
        with (
            mock.patch(
                "hope_mcp_server.core.validate_julia_command",
                return_value=("julia-test", None),
            ),
            mock.patch("hope_mcp_server.core._launch_job") as launch,
        ):
            second = hope_run_holistic(
                "ModelCases/gtep_case",
                "ModelCases/pcm_case",
                request_id="state-canonical",
                solver="highs",
            )
        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["reused"])
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
