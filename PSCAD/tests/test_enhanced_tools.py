import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import os

# Import the tools we want to test
from pscad_mcp.tools.project_tools import (
    get_component_parameters, 
    set_component_parameters,
    validate_component_parameters,
    get_project_settings
)
from pscad_mcp.tools.simset_tools import list_simulation_sets, run_simulation_set

class TestEnhancedPSCADTools(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Setup mocks for the PSCAD hierarchy
        self.mock_pscad = MagicMock()
        self.mock_project = MagicMock()
        self.mock_component = MagicMock()
        self.mock_sim_set = MagicMock()
        
        # Configure the hierarchy
        self.mock_pscad.project.return_value = self.mock_project
        self.mock_project.component.return_value = self.mock_component
        self.mock_project.simulation_set.return_value = self.mock_sim_set
        
        # Patch the connection manager to return our mock pscad
        self.conn_patcher = patch('pscad_mcp.tools.project_tools.pscad_manager')
        self.mock_manager = self.conn_patcher.start()
        self.mock_manager.pscad = self.mock_pscad
        
        # Also patch for simset tools
        self.simset_conn_patcher = patch('pscad_mcp.tools.simset_tools.pscad_manager')
        self.mock_simset_manager = self.simset_conn_patcher.start()
        self.mock_simset_manager.pscad = self.mock_pscad

        # Mock the robust executor to just run the function
        self.exec_patcher = patch('pscad_mcp.core.executor.robust_executor.run_safe', 
                                  side_effect=lambda f, *args, **kwargs: f(*args, **kwargs))
        self.mock_executor = self.exec_patcher.start()

    def tearDown(self):
        self.conn_patcher.stop()
        self.simset_conn_patcher.stop()
        self.exec_patcher.stop()

    async def test_get_component_parameters(self):
        """Test retrieving parameters from a mock component."""
        self.mock_component.parameters.return_value = {"KV": 138.0, "Name": "Bus1"}
        
        result = await get_component_parameters("TestProj", 101)
        
        self.assertEqual(result["KV"], 138.0)
        self.mock_project.component.assert_called_with(101)

    async def test_validate_parameters_success(self):
        """Test parameter validation against a mock range."""
        # Mock the range() method found in enriched docs
        self.mock_component.range.return_value = (0.0, 200.0)
        
        params_to_test = {"KV": 138.0}
        result = await validate_component_parameters("TestProj", 101, params_to_test)
        
        self.assertTrue(result["KV"]["valid"])
        self.assertEqual(result["KV"]["range"], "(0.0, 200.0)")

    async def test_validate_parameters_error(self):
        """Test validation behavior when a parameter doesn't exist."""
        self.mock_component.range.side_effect = Exception("No range defined")
        
        params_to_test = {"InvalidParam": 1.0}
        result = await validate_component_parameters("TestProj", 101, params_to_test)
        
        self.assertFalse(result["InvalidParam"]["valid"])
        self.assertIn("No range defined", result["InvalidParam"]["error"])

    async def test_list_simulation_sets(self):
        """Test listing simulation sets."""
        set1 = MagicMock()
        set1.name = "Batch1"
        self.mock_project.simulation_sets.return_value = [set1]
        
        result = await list_simulation_sets("TestProj")
        
        self.assertIn("Batch1", result)
        self.assertEqual(len(result), 1)

    async def test_run_simulation_set(self):
        """Test triggering a simulation set run."""
        result = await run_simulation_set("TestProj", "Batch1")
        
        self.assertIn("started", result)
        self.mock_sim_set.run.assert_called_once()

    async def test_get_project_settings(self):
        """Test retrieving project settings."""
        self.mock_project.parameters.return_value = {"Duration": "0.5", "TimeStep": "50"}

        result = await get_project_settings("TestProj")

        self.assertEqual(result["Duration"], "0.5")
        self.mock_project.parameters.assert_called_once()

if __name__ == '__main__':
    unittest.main()
