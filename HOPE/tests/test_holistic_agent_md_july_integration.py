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
    hope_audit_holistic_study,
    hope_holistic_study_status,
    hope_launch_holistic_study,
    hope_prepare_holistic_validation_study,
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
    def test_annual_gtep_july_pcm_multi_agent_study_is_auditable(self) -> None:
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
        warmup_hours = int(
            os.environ.get("HOPE_HOLISTIC_AGENT_MD_JULY_WARMUP_HOURS", "48")
        )
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

        study_id = f"md-rps20-month-{uuid.uuid4().hex}"
        launch: dict | None = None
        with tempfile.TemporaryDirectory(
            prefix="hope-md-july-agent-",
            dir=str(work_parent) if work_parent is not None else None,
            # Cloud-sync clients on Windows can briefly retain a handle after
            # Julia exits.  Cleanup residue must not turn a scientifically
            # successful integration run into a failed test result.
            ignore_cleanup_errors=True,
        ) as tmp:
            temporary_root = Path(tmp)
            runs_root = temporary_root / "agent-runs"
            studies_root = temporary_root / "agent-studies"
            with mock.patch.dict(
                "os.environ",
                {
                    "HOPE_REPO_ROOT": str(REPO_ROOT),
                    "HOPE_MODELCASES_PATH": str(source_modelcases),
                    "HOPE_AGENT_RUNS_ROOT": str(runs_root),
                    "HOPE_AGENT_STUDIES_ROOT": str(studies_root),
                },
                clear=False,
            ):
                try:
                    prepared = hope_prepare_holistic_validation_study(
                        study_id=study_id,
                        evaluation_month=month,
                        warmup_hours=warmup_hours,
                        solver=solver,
                        agent_label="integration-coordinator",
                    )
                    self.assertTrue(prepared["ok"], prepared)
                    validation_slice = yaml.safe_load(
                        Path(prepared["preparation"]["validation_slice_path"]).read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertEqual(validation_slice["gtep_hours"], 8760)
                    self.assertEqual(validation_slice["pcm_month"], month)
                    self.assertGreater(validation_slice["pcm_hours"], 0)
                    self.assertEqual(
                        validation_slice["pcm_warmup_hours"], warmup_hours
                    )
                    self.assertEqual(
                        validation_slice["pcm_hours"],
                        validation_slice["pcm_evaluation_hours"] + warmup_hours,
                    )
                    self.assertEqual(
                        validation_slice["pcm_evaluation_start_hour"],
                        warmup_hours + 1,
                    )
                    if month == 7:
                        self.assertEqual(validation_slice["pcm_evaluation_hours"], 744)

                    launch = hope_launch_holistic_study(
                        study_id,
                        agent_label="integration-executor",
                    )
                    self.assertTrue(launch["ok"], launch)
                    self.assertFalse(launch["reused"])

                    deadline = time.monotonic() + timeout_seconds
                    next_progress = 0.0
                    while True:
                        status = hope_holistic_study_status(study_id)
                        state = status.get("status")
                        if state in ("ready_for_audit", "failed"):
                            break
                        self.assertTrue(status["ok"], status)
                        now = time.monotonic()
                        if now >= next_progress:
                            print(
                                "High-resolution holistic agent test status: "
                                f"{state}; run={status.get('run', {}).get('status', 'unknown')}",
                                flush=True,
                            )
                            next_progress = now + 30.0
                        if now >= deadline:
                            self.fail(f"Holistic study timed out: {status}")
                        time.sleep(5.0)

                    self.assertTrue(status["ok"], status)
                    self.assertEqual(state, "ready_for_audit", status)
                    result = status["run"]["result"]
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

                    _holistic_request_jobs.pop(study_id, None)
                    recovered = hope_holistic_study_status(study_id)
                    self.assertTrue(recovered["ok"], recovered)
                    self.assertEqual(recovered["status"], "ready_for_audit")
                    self.assertTrue(
                        recovered["run"]["result"]["coverage_all_passed"]
                    )

                    audited = hope_audit_holistic_study(
                        study_id,
                        agent_label="integration-auditor",
                    )
                    self.assertTrue(audited["ok"], audited)
                    self.assertEqual(audited["status"], "accepted")
                    self.assertTrue(audited["audit"]["accepted"])
                    self.assertEqual(
                        set(audited["receipts"]),
                        {"coordinator", "executor", "auditor"},
                    )

                    repeated = hope_prepare_holistic_validation_study(
                        study_id=study_id,
                        evaluation_month=month,
                        warmup_hours=warmup_hours,
                        solver=solver,
                    )
                    self.assertTrue(repeated["ok"], repeated)
                    self.assertTrue(repeated["reused"])
                    relaunched = hope_launch_holistic_study(study_id)
                    self.assertTrue(relaunched["ok"], relaunched)
                    self.assertTrue(relaunched["reused"])
                    self.assertEqual(relaunched["status"], "accepted")
                    self.assertEqual(len(list(runs_root.iterdir())), 1)
                finally:
                    _holistic_request_jobs.pop(study_id, None)
                    if launch is not None:
                        run = launch.get("run") or {}
                        job = _jobs.pop(run.get("job_id", ""), None)
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
