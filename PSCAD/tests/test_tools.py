import asyncio
import os
import unittest
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.server.mcpserver import MCPServer as FastMCP
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.tools.app_tools import register_app_tools, get_pscad_status, read_documentation
from pscad_mcp.tools.data_tools import _resolve_psout
from pscad_mcp.tools.project_tools import (
    get_build_messages,
    get_run_status,
    load_projects,
    find_components,
    register_project_tools,
    run_project,
    run_project_to_completion,
)
from pscad_mcp.utils.doc_manager import DocumentationManager


class TestAllTools(unittest.IsolatedAsyncioTestCase):
    """Comprehensive tool logic testing covering edge and error cases."""

    async def asyncSetUp(self):
        self.mcp = FastMCP("Test")
        register_project_tools(self.mcp)
        register_app_tools(self.mcp)
        self.mock_pscad = MagicMock()
        pscad_manager._pscad = self.mock_pscad
        self.os_patcher = patch(
            "pscad_mcp.core.connection_manager.PSCADConnectionManager.is_process_running",
            return_value=True,
        )
        self.os_patcher.start()

    async def asyncTearDown(self):
        self.os_patcher.stop()

    async def test_get_status_unresponsive(self):
        self.mock_pscad.is_busy.side_effect = Exception("COM Error")
        result = await get_pscad_status()
        self.assertEqual(result["connected"], False)

    async def test_documentation_name_is_not_a_path(self):
        result = await read_documentation("/tmp/secret")
        self.assertIn("dotted ASCII Python module name", result)

    async def test_documentation_manager_does_not_write_at_import(self):
        manager = DocumentationManager("missing/docs")
        self.assertFalse(os.path.exists(manager.base_dir))

    @unittest.skipIf(os.name == "nt", "POSIX symlink semantics")
    async def test_out_sibling_psout_is_checked_after_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            allowed = root / "allowed"
            allowed.mkdir()
            legacy = allowed / "run.out"
            legacy.write_text("legacy")
            outside = root / "outside.psout"
            outside.write_text("output")
            (allowed / "run.psout").symlink_to(outside)
            with patch.dict(os.environ, {"POWERIO_MCP_ALLOWED_ROOTS": str(allowed)}, clear=False):
                with self.assertRaisesRegex(ValueError, "outside allowed MCP roots"):
                    await _resolve_psout(str(legacy))

    async def test_load_nonexistent_project(self):
        self.mock_pscad.load.side_effect = FileNotFoundError("File not found")
        with self.assertRaises(Exception):
            await load_projects(filenames=["C:\\missing.pscx"])

    async def test_run_unlicensed_project(self):
        self.mock_pscad.licensed.return_value = False
        result = await run_project(project_name="test")
        self.assertFalse(result["started"])
        self.assertIn("not licensed", result["error"])

    async def test_find_no_components(self):
        self.mock_pscad.project.return_value.find_all.return_value = []
        self.assertEqual(await find_components(project_name="test", name="Ghost"), [])

    async def test_invalid_project_name(self):
        self.mock_pscad.project.side_effect = Exception("Project not found")
        with self.assertRaises(Exception):
            await run_project(project_name="unknown")


class TestRunProjectToCompletion(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pscad = MagicMock()
        self.project = MagicMock()
        pscad_manager._pscad = self.pscad
        # The connection manager validates process and heartbeat health even
        # when a mocked PSCAD handle is installed; isolate those OS/RMI checks.
        self.connection_checks = patch.multiple(
            "pscad_mcp.core.connection_manager.PSCADConnectionManager",
            is_process_running=MagicMock(return_value=True),
        )
        self.connection_checks.start()
        self.pscad.is_alive.return_value = True
        self.pscad.is_busy.return_value = False
        self.pscad.licensed.return_value = True
        self.pscad.project.return_value = self.project
        self.project.start = MagicMock()
        self.project.messages.return_value = []
        self.progress = patch(
            "pscad_mcp.tools.project_tools._report_progress",
            new=AsyncMock(),
        )
        self.progress.start()

    async def asyncTearDown(self):
        self.progress.stop()
        self.connection_checks.stop()

    async def test_completion_requires_observing_running(self):
        self.project.run_status.side_effect = [
            ("Build", 0),
            ("Run", 25),
            ("Run", 100),
            (None, 100),
        ]
        with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new=AsyncMock()):
            result = await run_project_to_completion("case", timeout_seconds=5, poll_interval_seconds=0.001)
        self.assertEqual(result["final_status"], "completed")
        self.assertEqual(result["progress"], 100)
        self.project.start.assert_called_once()

    async def test_compilation_error_never_claims_completion(self):
        error = MagicMock(status="Error", text="Fortran compiler missing", name="Compiler")
        self.project.run_status.return_value = (None, 0)
        self.project.messages.return_value = [error]
        result = await run_project_to_completion("case", timeout_seconds=2, poll_interval_seconds=0.001)
        self.assertEqual(result["final_status"], "build_failed")
        self.assertEqual(result["status"], "failed")
        self.assertIn("Fortran compiler missing", result["errors"][0]["text"])

    async def test_idle_without_errors_is_not_reported_as_completed(self):
        self.project.run_status.return_value = ("Idle", 0)
        result = await run_project_to_completion("case", timeout_seconds=2, poll_interval_seconds=0.001)
        self.assertEqual(result["final_status"], "not_started")
        self.assertNotEqual(result["status"], "completed")

    async def test_timeout_is_explicit(self):
        self.project.run_status.return_value = ("Run", 20)
        with patch("pscad_mcp.tools.project_tools.time.monotonic", side_effect=[0, 0, 2, 2, 2, 2, 2]):
            with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new=AsyncMock()):
                result = await run_project_to_completion("case", timeout_seconds=1, poll_interval_seconds=0.001)
        self.assertEqual(result["final_status"], "timeout")
        self.assertEqual(result["status"], "failed")

    async def test_start_exception_means_not_started(self):
        self.project.start.side_effect = RuntimeError("PSCAD rejected start")
        result = await run_project_to_completion("case", timeout_seconds=1)
        self.assertEqual(result["final_status"], "not_started")
        self.assertFalse(result["started"])

    async def test_unlicensed_is_not_started(self):
        self.pscad.licensed.return_value = False
        result = await run_project_to_completion("case")
        self.assertEqual(result["final_status"], "not_started")
        self.assertFalse(result["started"])

    async def test_invalid_timeout_rejected(self):
        result = await run_project_to_completion("case", timeout_seconds=0)
        self.assertEqual(result["final_status"], "invalid_timeout")

    async def test_status_query_failure_is_failure_not_success(self):
        self.project.run_status.side_effect = RuntimeError("RMI unavailable")
        result = await run_project_to_completion("case", timeout_seconds=1)
        self.assertEqual(result["final_status"], "status_error")


if __name__ == "__main__":
    unittest.main()
