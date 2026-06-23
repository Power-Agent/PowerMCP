import asyncio
import unittest
from unittest.mock import MagicMock, patch
import os
from pscad_mcp.tools.project_tools import register_project_tools, run_project, load_projects, find_components
from pscad_mcp.tools.app_tools import register_app_tools, get_pscad_status
from pscad_mcp.core.connection_manager import pscad_manager
from mcp.server.fastmcp import FastMCP

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
