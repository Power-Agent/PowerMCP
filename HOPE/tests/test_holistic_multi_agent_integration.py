from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

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
    hope_prepare_holistic_study,
)


@unittest.skipUnless(
    os.environ.get("HOPE_RUN_HOLISTIC_MULTI_AGENT_INTEGRATION") == "1",
    "set HOPE_RUN_HOLISTIC_MULTI_AGENT_INTEGRATION=1 to run the solver-backed multi-agent test",
)
class HolisticMultiAgentIntegrationTests(unittest.TestCase):
    def test_coordinator_executor_and_auditor_survive_reconnect(self) -> None:
        gtep_case = "MD_GTEP_restricted_linkage_case"
        pcm_case = "MD_PCM_restricted_linkage_case"
        for case_id in (gtep_case, pcm_case):
            if not (REPO_ROOT / "ModelCases" / case_id).is_dir():
                self.skipTest(f"ModelCases/{case_id} is unavailable")

        study_id = f"multi-agent-integration-{uuid.uuid4().hex}"
        solver = os.environ.get("HOPE_HOLISTIC_AGENT_SOLVER", "highs")
        timeout_seconds = float(os.environ.get("HOPE_HOLISTIC_AGENT_TIMEOUT", "900"))

        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            with mock.patch.dict(
                "os.environ",
                {
                    "HOPE_REPO_ROOT": str(REPO_ROOT),
                    "HOPE_AGENT_RUNS_ROOT": str(temporary_path / "runs"),
                    "HOPE_AGENT_STUDIES_ROOT": str(temporary_path / "studies"),
                },
                clear=False,
            ):
                prepared = hope_prepare_holistic_study(
                    gtep_case,
                    pcm_case,
                    study_id=study_id,
                    solver=solver,
                    agent_label="integration-coordinator",
                )
                self.assertTrue(prepared["ok"], prepared)
                self.assertEqual(prepared["status"], "prepared")

                launched = hope_launch_holistic_study(
                    study_id,
                    agent_label="integration-executor",
                )
                self.assertTrue(launched["ok"], launched)

                deadline = time.monotonic() + timeout_seconds
                while True:
                    status = hope_holistic_study_status(study_id)
                    state = status.get("status")
                    if state in ("ready_for_audit", "failed", "rejected", "accepted"):
                        break
                    self.assertTrue(status["ok"], status)
                    if time.monotonic() >= deadline:
                        self.fail(f"Multi-agent study timed out: {status}")
                    time.sleep(2.0)

                self.assertTrue(status["ok"], status)
                self.assertEqual(state, "ready_for_audit")

                # Simulate an MCP/client reconnect before the independent audit.
                _holistic_request_jobs.pop(study_id, None)
                completed_job = _jobs.pop(launched["run"]["job_id"], None)
                if completed_job is not None:
                    for stream in (completed_job.process.stdout, completed_job.process.stderr):
                        if stream is not None:
                            stream.close()

                audited = hope_audit_holistic_study(
                    study_id,
                    agent_label="integration-auditor",
                )
                self.assertTrue(audited["ok"], audited)
                self.assertEqual(audited["status"], "accepted")
                self.assertTrue(audited["audit"]["accepted"])
                self.assertEqual(
                    audited["audit"]["passed_checks"],
                    audited["audit"]["total_checks"],
                )
                self.assertEqual(
                    set(audited["receipts"]),
                    {"coordinator", "executor", "auditor"},
                )


if __name__ == "__main__":
    unittest.main()
