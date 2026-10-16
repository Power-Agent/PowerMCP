import asyncio
import unittest
from unittest.mock import MagicMock, patch
import os
from pathlib import Path
import tempfile
from pscad_mcp.tools.project_tools import register_project_tools, run_project, load_projects, find_components
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
