from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(
    os.environ.get("HOPE_REPO_ROOT", Path(__file__).resolve().parents[3])
).expanduser().resolve()
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.core import (  # noqa: E402
    _holistic_request_jobs,
    _jobs,
    hope_holistic_status,
    hope_run_holistic,
)


def configured_modelcases_root() -> Path:
    configured = os.environ.get("HOPE_MODELCASES_PATH")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (REPO_ROOT / "ModelCases").resolve()
    )


@unittest.skipUnless(
    os.environ.get("HOPE_RUN_HOLISTIC_AGENT_MD_JULY_INTEGRATION") == "1",
    "set HOPE_RUN_HOLISTIC_AGENT_MD_JULY_INTEGRATION=1 to run the high-resolution agent test",
)
class MarylandJulyHolisticAgentIntegrationTests(unittest.TestCase):
    def test_annual_gtep_july_pcm_request_is_agent_safe(self) -> None:
        source_modelcases = configured_modelcases_root()
        builder = (
            source_modelcases
            / "tools"
            / "md_transmission_case_related"
            / "build_md_rps20_full8760_holistic_pair.py"
        )
        required_cases = (
            "MD_GTEP_RPS20_4zone_full8760_public_case",
            "MD_PCM_RPS20_transmission_full8760_public_case",
        )
        if not builder.is_file():
            self.skipTest(f"Maryland validation builder is unavailable: {builder}")
        for case_id in required_cases:
            if not (source_modelcases / case_id).is_dir():
                self.skipTest(f"Required ModelCase is unavailable: {case_id}")

        solver = os.environ.get("HOPE_HOLISTIC_AGENT_MD_JULY_SOLVER", "gurobi")
        month = int(os.environ.get("HOPE_HOLISTIC_AGENT_MD_JULY_MONTH", "7"))
        timeout_seconds = float(
            os.environ.get("HOPE_HOLISTIC_AGENT_MD_JULY_TIMEOUT", "3600")
        )
        work_parent_value = os.environ.get("HOPE_AGENT_TEST_WORK_ROOT")
        work_parent = (
            Path(work_parent_value).expanduser().resolve()
            if work_parent_value
            else None
        )
        if work_parent is not None:
            work_parent.mkdir(parents=True, exist_ok=True)

        request_id = f"md-rps20-july-{uuid.uuid4().hex}"
        launch: dict | None = None
        with tempfile.TemporaryDirectory(
            prefix="hope-md-july-agent-",
            dir=str(work_parent) if work_parent is not None else None,
        ) as tmp:
            temporary_root = Path(tmp)
            generated_cases = temporary_root / "model-cases"
            runs_root = temporary_root / "agent-runs"

            print(
                f"Preparing annual-GTEP/month-{month}-PCM validation cases...",
                flush=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(builder),
                    "--validation-month",
                    str(month),
                    "--validation-root",
                    str(generated_cases),
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            validation_slice = yaml.safe_load(
                (generated_cases / "validation_slice.yml").read_text(encoding="utf-8")
            )
            self.assertEqual(validation_slice["gtep_hours"], 8760)
            self.assertEqual(validation_slice["pcm_month"], month)
            self.assertGreater(validation_slice["pcm_hours"], 0)
            if month == 7:
                self.assertEqual(validation_slice["pcm_hours"], 744)

            with mock.patch.dict(
                "os.environ",
                {
                    "HOPE_REPO_ROOT": str(REPO_ROOT),
                    "HOPE_MODELCASES_PATH": str(generated_cases),
                    "HOPE_AGENT_RUNS_ROOT": str(runs_root),
                },
                clear=False,
            ):
                try:
                    launch = hope_run_holistic(
                        "gtep_case",
                        "pcm_case",
                        request_id=request_id,
                        solver=solver,
                    )
                    self.assertTrue(launch["ok"], launch)
                    self.assertFalse(launch["reused"])

                    deadline = time.monotonic() + timeout_seconds
                    next_progress = 0.0
                    while True:
                        status = hope_holistic_status(request_id)
                        state = status.get("status")
                        if state in ("done", "published", "failed", "cancelled"):
                            break
                        self.assertTrue(status["ok"], status)
                        now = time.monotonic()
                        if now >= next_progress:
                            print(
                                "High-resolution holistic agent test status: "
                                f"{state}; elapsed={status.get('elapsed_seconds', 'unknown')}s",
                                flush=True,
                            )
                            next_progress = now + 30.0
                        if now >= deadline:
                            self.fail(f"Holistic request timed out: {status}")
                        time.sleep(5.0)

                    self.assertTrue(status["ok"], status)
                    self.assertIn(state, ("done", "published"), status)
                    result = status["result"]
                    self.assertTrue(result["handoff_valid"])
                    self.assertTrue(result["transfer_valid"])
                    self.assertTrue(result["coverage_evaluated"])
                    self.assertTrue(result["coverage_all_passed"])

                    coverage_path = Path(result["coverage_paths"]["coverage_yaml"])
                    coverage = yaml.safe_load(coverage_path.read_text(encoding="utf-8"))
                    metrics = coverage["metrics"]
                    self.assertTrue(coverage["all_passed"])
                    self.assertEqual(metrics["gtep_termination_status"], "OPTIMAL")
                    self.assertEqual(metrics["pcm_termination_status"], "OPTIMAL")
                    self.assertTrue(metrics["source_gtep_unchanged"])
                    self.assertTrue(metrics["source_pcm_unchanged"])
                    self.assertGreater(float(metrics["new_generation_mw"]), 0.0)
                    self.assertGreater(
                        float(metrics["pcm_new_generation_dispatch_mwh"]), 0.0
                    )
                    self.assertGreater(
                        float(metrics["operational_template_assets"]), 0.0
                    )
                    self.assertTrue(metrics["new_thermal_generation_all_uc"])
                    self.assertGreater(
                        float(metrics["gtep_operating_reserve_mwh"]), 0.0
                    )
                    self.assertGreater(
                        float(metrics["pcm_operating_reserve_mwh"]), 0.0
                    )
                    self.assertLessEqual(float(metrics["pcm_load_shedding_mwh"]), 1e-6)
                    self.assertLessEqual(float(metrics["gtep_rps_slack_mwh"]), 1e-6)
                    self.assertLessEqual(float(metrics["pcm_rps_slack_mwh"]), 1e-6)

                    _holistic_request_jobs.pop(request_id, None)
                    recovered = hope_holistic_status(request_id)
                    self.assertTrue(recovered["ok"], recovered)
                    self.assertEqual(recovered["status"], "published")
                    self.assertTrue(recovered["result"]["coverage_all_passed"])

                    repeated = hope_run_holistic(
                        "gtep_case",
                        "pcm_case",
                        request_id=request_id,
                        solver=solver,
                    )
                    self.assertTrue(repeated["ok"], repeated)
                    self.assertTrue(repeated["reused"])
                    self.assertEqual(repeated["status"], "published")
                    self.assertEqual(len(list(runs_root.iterdir())), 1)
                finally:
                    _holistic_request_jobs.pop(request_id, None)
                    if launch is not None:
                        job = _jobs.pop(launch.get("job_id", ""), None)
                        if job is not None:
                            if job.process.poll() is None:
                                job.process.terminate()
                                try:
                                    job.process.wait(timeout=10)
                                except subprocess.TimeoutExpired:
                                    job.process.kill()
                                    job.process.wait(timeout=10)
                            for stream in (job.process.stdout, job.process.stderr):
                                if stream is not None:
                                    stream.close()


if __name__ == "__main__":
    unittest.main()
