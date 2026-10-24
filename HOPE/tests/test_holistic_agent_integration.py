from __future__ import annotations

import os
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


@unittest.skipUnless(
    os.environ.get("HOPE_RUN_HOLISTIC_AGENT_INTEGRATION") == "1",
    "set HOPE_RUN_HOLISTIC_AGENT_INTEGRATION=1 to run the solver-backed agent test",
)
class HolisticAgentIntegrationTests(unittest.TestCase):
    def test_restricted_gtep_pcm_request_survives_reconnect(self) -> None:
        gtep_case = "MD_GTEP_restricted_linkage_case"
        pcm_case = "MD_PCM_restricted_linkage_case"
        for case_id in (gtep_case, pcm_case):
            if not (REPO_ROOT / "ModelCases" / case_id).is_dir():
                self.skipTest(f"ModelCases/{case_id} is unavailable")

        request_id = f"agent-integration-{uuid.uuid4().hex}"
        solver = os.environ.get("HOPE_HOLISTIC_AGENT_SOLVER", "highs")
        timeout_seconds = float(os.environ.get("HOPE_HOLISTIC_AGENT_TIMEOUT", "900"))

        with tempfile.TemporaryDirectory() as run_root:
            with mock.patch.dict(
                "os.environ",
                {
                    "HOPE_REPO_ROOT": str(REPO_ROOT),
                    "HOPE_AGENT_RUNS_ROOT": run_root,
                },
                clear=False,
            ):
                launch = hope_run_holistic(
                    gtep_case,
                    pcm_case,
                    request_id=request_id,
                    solver=solver,
                )
                self.assertTrue(launch["ok"], launch)

                deadline = time.monotonic() + timeout_seconds
                while True:
                    status = hope_holistic_status(request_id)
                    state = status.get("status")
                    if state in ("done", "failed", "cancelled"):
                        break
                    self.assertTrue(status["ok"], status)
                    if time.monotonic() >= deadline:
                        self.fail(f"Holistic request timed out: {status}")
                    time.sleep(2.0)

                self.assertTrue(status["ok"], status)
                self.assertEqual(state, "done")
                result = status["result"]
                self.assertTrue(result["handoff_valid"])
                self.assertTrue(result["transfer_valid"])
                self.assertTrue(result["coverage_evaluated"])
                self.assertTrue(result["coverage_all_passed"])

                coverage_path = Path(result["coverage_paths"]["coverage_yaml"])
                coverage = yaml.safe_load(coverage_path.read_text(encoding="utf-8"))
                self.assertTrue(coverage["all_passed"])
                self.assertEqual(coverage["metrics"]["gtep_termination_status"], "OPTIMAL")
                self.assertEqual(coverage["metrics"]["pcm_termination_status"], "OPTIMAL")
                self.assertTrue(coverage["metrics"]["source_gtep_unchanged"])
                self.assertTrue(coverage["metrics"]["source_pcm_unchanged"])

                _holistic_request_jobs.pop(request_id, None)
                completed_job = _jobs.pop(launch["job_id"], None)
                if completed_job is not None:
                    for stream in (completed_job.process.stdout, completed_job.process.stderr):
                        if stream is not None:
                            stream.close()
                recovered = hope_holistic_status(request_id)
                self.assertTrue(recovered["ok"], recovered)
                self.assertEqual(recovered["status"], "done")
                self.assertTrue(recovered["result"]["coverage_all_passed"])


if __name__ == "__main__":
    unittest.main()
