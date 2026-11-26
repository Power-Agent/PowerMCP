import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from pathlib import Path
import tempfile
import time
from pscad_mcp.tools.project_tools import (
    register_project_tools,
    run_project,
    run_project_to_completion,
    load_projects,
    find_components,
)
from pscad_mcp.tools.app_tools import register_app_tools, get_pscad_status, read_documentation
from pscad_mcp.tools.data_tools import _resolve_psout
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.utils.doc_manager import DocumentationManager
from mcp.server.mcpserver import MCPServer as FastMCP

class TestAllTools(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive tool logic testing covering edge and error cases.
    """

    async def asyncSetUp(self):
        self.mcp = FastMCP("Test")
        # Registering tools is not strictly necessary for unit tests if we call functions directly,
        # but it validates registration logic.
        register_project_tools(self.mcp)
        register_app_tools(self.mcp)
        # Mock the PSCAD instance for all tests
        self.mock_pscad = MagicMock()
        pscad_manager._pscad = self.mock_pscad
        # Mock OS check
        self.os_patcher = patch('pscad_mcp.core.connection_manager.PSCADConnectionManager.is_process_running', return_value=True)
        self.os_patcher.start()

    async def asyncTearDown(self):
        self.os_patcher.stop()

    # --- Connection Tools ---
    
    async def test_get_status_unresponsive(self):
        """Edge case: PSCAD is running but RMI call fails."""
        self.mock_pscad.is_busy.side_effect = Exception("COM Error")
        result = await get_pscad_status()
        self.assertEqual(result["connected"], False)

    async def test_documentation_name_is_not_a_path(self):
        result = await read_documentation("/tmp/secret")
        self.assertIn("dotted ASCII Python module name", result)

    async def test_documentation_manager_does_not_write_at_import(self):
        with self.subTest("constructor is read-only"):
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

            with patch.dict(
                os.environ, {"POWERIO_MCP_ALLOWED_ROOTS": str(allowed)}, clear=False
            ):
                with self.assertRaisesRegex(ValueError, "outside allowed MCP roots"):
                    await _resolve_psout(str(legacy))

    # --- Project Tools ---

    async def test_load_nonexistent_project(self):
        """Edge case: Loading a file that doesn't exist on disk."""
        self.mock_pscad.load.side_effect = FileNotFoundError("File not found")
        with self.assertRaises(Exception): 
             await load_projects(filenames=["C:\\missing.pscx"])

    async def test_run_unlicensed_project(self):
        """Edge case: Attempting simulation without a valid license."""
        self.mock_pscad.licensed.return_value = False
        result = await run_project(project_name="test")
        self.assertFalse(result["started"])
        self.assertIn("not licensed", result["error"])

    async def test_run_to_completion_reports_progress_and_waits_for_idle(self):
        mock_project = MagicMock()
        mock_project.run_status.side_effect = [
            (None, None),  # preflight: idle before starting this request
            ("Build", None),
            ("Run", 10),
            ("Run", 100),
            (None, None),
        ]
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
            result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "completed")
        mock_project.start.assert_called_once()
        self.assertGreaterEqual(ctx.report_progress.await_count, 4)
        reported = [call.args[0] for call in ctx.report_progress.await_args_list]
        self.assertEqual(reported, sorted(reported))
        self.assertTrue(all(call.kwargs.get("total") == 100 for call in ctx.report_progress.await_args_list))
        self.assertTrue(any(call.args[0] == 10 for call in ctx.report_progress.await_args_list))

    async def test_run_to_completion_reports_build_failure_not_success(self):
        mock_project = MagicMock()
        mock_project.run_status.side_effect = [
            (None, None),  # preflight
            ("Build", None),
            (None, None),
        ]
        build_error = MagicMock()
        build_error.status = "Error"
        build_error.text = "compiler failed"
        build_error.name = "EMTDC"
        mock_project.messages.side_effect = [[], [build_error]]  # baseline, then new build error
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
            result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "build_failed")
        self.assertIn("compiler failed", result["errors"][0]["text"])
        self.assertNotEqual(result["status"], "completed")

    async def test_run_to_completion_does_not_treat_idle_as_success(self):
        mock_project = MagicMock()
        mock_project.run_status.side_effect = [(None, None)] * 5  # preflight plus four idle polls
        mock_project.messages.return_value = []
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
            result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "not_completed")
        self.assertNotEqual(result["status"], "completed")

    async def test_run_to_completion_timeout_does_not_cancel_pscad(self):
        mock_project = MagicMock()
        mock_project.run_status.side_effect = [(None, None)] + [("Run", 12)] * 20
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()
        real_sleep = asyncio.sleep
        requested_delays = []

        async def elapse_time(delay):
            requested_delays.append(delay)
            await real_sleep(0.01)

        with patch(
            "pscad_mcp.tools.project_tools.asyncio.sleep",
            new=elapse_time,
        ):
            result = await run_project_to_completion(
                "test", ctx, timeout_seconds=0.05
            )

        self.assertTrue(requested_delays)
        self.assertLessEqual(requested_delays[0], 0.05)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["last_state"], "running")
        mock_project.start.assert_called_once()


    async def test_run_to_completion_waits_through_startup_idle(self):
        mock_project = MagicMock()
        mock_project.run_status.side_effect = [
            (None, None),  # preflight idle
            (None, None),  # PSCAD has not entered Build yet
            ("Build", None),
            ("Run", 50),
            (None, None),
        ]
        mock_project.messages.return_value = []
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
            result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["message"].startswith("PSCAD was observed running"))

    async def test_run_to_completion_accepts_short_run_between_polls(self):
        with tempfile.TemporaryDirectory() as output_dir:
            mock_project = MagicMock()
            mock_project.temp_folder = output_dir
            output_file = Path(output_dir) / "short.psout"
            mock_project.start.side_effect = lambda: output_file.write_text("fresh output")
            mock_project.run_status.side_effect = [
                (None, None),  # preflight idle
                ("Build", None),
                ("Build", None),
                (None, None),  # Run completed between status samples
            ]
            stale_error = MagicMock()
            stale_error.status = "Error"
            stale_error.text = "error from the previous build"
            stale_error.name = "EMTDC"
            # The same old diagnostic remains visible after this run; it must
            # not be attributed to the current build.
            mock_project.messages.side_effect = [[stale_error], [stale_error]]
            self.mock_pscad.project.return_value = mock_project
            ctx = MagicMock()
            ctx.report_progress = AsyncMock()

            with patch.dict(os.environ, {"POWERIO_MCP_ALLOWED_ROOTS": output_dir}):
                with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
                    result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["errors"], [])
        self.assertIn("output file was created or updated", result["message"])

    async def _run_short_run_writing_output_with_mtime_offset(self, offset_ns):
        """Run a missed short run whose output mtime is shifted from the write time."""
        with tempfile.TemporaryDirectory() as output_dir:
            mock_project = MagicMock()
            mock_project.temp_folder = output_dir
            output_file = Path(output_dir) / "short.psout"

            def start():
                output_file.write_text("fresh output")
                mtime_ns = time.time_ns() + offset_ns
                os.utime(output_file, ns=(mtime_ns, mtime_ns))

            mock_project.start.side_effect = start
            mock_project.run_status.side_effect = [
                (None, None),  # preflight idle
                ("Build", None),
                ("Build", None),
                (None, None),  # Run completed between status samples
            ]
            mock_project.messages.side_effect = [[], []]
            self.mock_pscad.project.return_value = mock_project
            ctx = MagicMock()
            ctx.report_progress = AsyncMock()

            with patch.dict(os.environ, {"POWERIO_MCP_ALLOWED_ROOTS": output_dir}):
                with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
                    return await run_project_to_completion("test", ctx)

    async def test_run_to_completion_tolerates_coarse_filesystem_mtime(self):
        # Filesystem clocks are coarser than time.time_ns() (kernel ticks on
        # Linux, 2 s on FAT), so output written just after start can carry an
        # mtime slightly before the recorded run start.
        result = await self._run_short_run_writing_output_with_mtime_offset(-1_000_000_000)

        self.assertEqual(result["status"], "completed")
        self.assertIn("output file was created or updated", result["message"])

    async def test_run_to_completion_rejects_output_far_older_than_run(self):
        # A file that appears with an old mtime (e.g. copied in with its
        # timestamp preserved) is not evidence that this run produced it.
        result = await self._run_short_run_writing_output_with_mtime_offset(-3600 * 1_000_000_000)

        self.assertEqual(result["status"], "not_completed")

    async def test_run_to_completion_does_not_accept_empty_output_as_completion(self):
        with tempfile.TemporaryDirectory() as output_dir:
            mock_project = MagicMock()
            mock_project.temp_folder = output_dir
            output_file = Path(output_dir) / "empty.psout"
            mock_project.start.side_effect = lambda: output_file.write_text("")
            mock_project.run_status.side_effect = [
                (None, None),  # preflight idle
                ("Build", None),
                ("Build", None),
                (None, None),  # Run was not observed; empty output is insufficient evidence
            ]
            mock_project.messages.side_effect = [[], []]
            self.mock_pscad.project.return_value = mock_project
            ctx = MagicMock()
            ctx.report_progress = AsyncMock()

            with patch.dict(os.environ, {"POWERIO_MCP_ALLOWED_ROOTS": output_dir}):
                with patch("pscad_mcp.tools.project_tools.asyncio.sleep", new_callable=AsyncMock):
                    result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "not_completed")
        self.assertIn("Completion cannot be confirmed", result["message"])

    async def test_run_to_completion_refuses_to_attach_to_existing_run(self):
        mock_project = MagicMock()
        mock_project.run_status.return_value = ("Run", 37)
        self.mock_pscad.project.return_value = mock_project
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        result = await run_project_to_completion("test", ctx)

        self.assertEqual(result["status"], "already_running")
        mock_project.start.assert_not_called()

    async def test_run_to_completion_rejects_invalid_timeout(self):
        ctx = MagicMock()
        ctx.report_progress = AsyncMock()

        with self.assertRaises(ValueError):
            await run_project_to_completion("test", ctx, timeout_seconds=0)

    async def test_find_no_components(self):
        """Edge case: Searching for components that don't exist."""
        mock_prj = MagicMock()
        mock_prj.find_all.return_value = []
        self.mock_pscad.project.return_value = mock_prj
        result = await find_components(project_name="test", name="Ghost")
        self.assertEqual(len(result), 0)

    async def test_invalid_project_name(self):
        """Edge case: Using a project name that isn't loaded."""
        self.mock_pscad.project.side_effect = Exception("Project not found")
        with self.assertRaises(Exception):
             await run_project(project_name="unknown")

if __name__ == "__main__":
    unittest.main()
