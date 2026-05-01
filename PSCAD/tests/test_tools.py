import asyncio
import unittest
from unittest.mock import MagicMock, patch
from pscad_mcp.tools.project_tools import (
    register_project_tools,
    run_project,
    load_projects,
    find_components,
    run_project_and_wait,
    set_component_parameters_safe,
)
from pscad_mcp.tools.app_tools import register_app_tools, get_pscad_status
from pscad_mcp.core.connection_manager import pscad_manager
from pscad_mcp.core.errors import (
    ErrorKind,
    classify_exception,
    values_equivalent,
)
from mcp.server.fastmcp import FastMCP

class TestAllTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mcp = FastMCP("Test")
        register_project_tools(self.mcp)
        register_app_tools(self.mcp)
        self.mock_pscad = MagicMock()
        pscad_manager._pscad = self.mock_pscad
        pscad_manager.invalidate_heartbeat()
        self.os_patcher = patch('pscad_mcp.core.connection_manager.PSCADConnectionManager.is_process_running', return_value=True)
        self.os_patcher.start()

    async def asyncTearDown(self):
        self.os_patcher.stop()
        pscad_manager.invalidate_heartbeat()

    # --- Connection Tools ---
    
    async def test_get_status_unresponsive(self):
        self.mock_pscad.is_busy.side_effect = Exception("COM Error")
        result = await get_pscad_status()
        self.assertEqual(result["connected"], False)

    # --- Project Tools ---

    async def test_load_nonexistent_project(self):
        self.mock_pscad.load.side_effect = FileNotFoundError("File not found")
        with self.assertRaises(Exception): 
             await load_projects(filenames=["C:\\missing.pscx"])

    async def test_run_unlicensed_project(self):
        self.mock_pscad.licensed.return_value = False
        result = await run_project(project_name="test")
        self.assertIn("not licensed", result)

    async def test_find_no_components(self):
        mock_prj = MagicMock()
        mock_prj.find_all.return_value = []
        self.mock_pscad.project.return_value = mock_prj
        result = await find_components(project_name="test", name="Ghost")
        self.assertEqual(len(result), 0)

    async def test_invalid_project_name(self):
        self.mock_pscad.project.side_effect = Exception("Project not found")
        with self.assertRaises(Exception):
             await run_project(project_name="unknown")

    # --- run_project_and_wait ---

    async def test_run_and_wait_happy_path(self):
        self.mock_pscad.licensed.return_value = True
        mock_prj = MagicMock()
        mock_prj.run_status.side_effect = [("Run", 50), ("Run", 90), (None, None)]
        mock_prj.output.return_value = "EMTDC complete."
        mock_prj.settings.return_value = {"output_filename": "case.out"}
        self.mock_pscad.project.return_value = mock_prj

        result = await run_project_and_wait(
            project_name="case", timeout_s=5.0, initial_poll_s=0.01, max_poll_s=0.05
        )

        self.assertTrue(result["ok"], msg=result)
        self.assertEqual(result["result"]["final_status"], "completed")
        self.assertEqual(result["result"]["output_messages"], "EMTDC complete.")
        self.assertEqual(result["result"]["output_file_path"], "case.out")
        mock_prj.run.assert_called_once()

    async def test_run_and_wait_unlicensed(self):
        self.mock_pscad.licensed.return_value = False
        mock_prj = MagicMock()
        self.mock_pscad.project.return_value = mock_prj

        result = await run_project_and_wait(project_name="case", timeout_s=1.0)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], ErrorKind.LICENSE.value)
        mock_prj.run.assert_not_called()

    async def test_run_and_wait_timeout(self):
        self.mock_pscad.licensed.return_value = True
        mock_prj = MagicMock()
        mock_prj.run_status.return_value = ("Run", 10)
        self.mock_pscad.project.return_value = mock_prj

        result = await run_project_and_wait(
            project_name="case",
            timeout_s=0.05,
            initial_poll_s=0.01,
            max_poll_s=0.02,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], ErrorKind.TIMEOUT.value)

    # --- set_component_parameters_safe ---

    async def test_safe_set_happy_path(self):
        mock_prj = MagicMock()
        mock_comp = MagicMock()
        mock_comp.range.return_value = (0, 1000)
        mock_comp.parameters.side_effect = [
            {"Tap": "1.00 [pu]"},
            None,
            {"Tap": "1.05 [pu]"},
        ]
        mock_prj.component.return_value = mock_comp
        self.mock_pscad.project.return_value = mock_prj

        result = await set_component_parameters_safe(
            project_name="case",
            component_id=42,
            parameters={"Tap": "1.05"},
        )

        self.assertTrue(result["ok"], msg=result)
        self.assertEqual(result["result"]["mismatches"], {})
        self.assertEqual(result["result"]["normalized_values"], {"Tap": "1.05 [pu]"})

    async def test_safe_set_invalid_param_blocks_write(self):
        mock_prj = MagicMock()
        mock_comp = MagicMock()
        mock_comp.range.side_effect = Exception("Parameter 'Bogus' not found")
        mock_prj.component.return_value = mock_comp
        self.mock_pscad.project.return_value = mock_prj

        result = await set_component_parameters_safe(
            project_name="case", component_id=42, parameters={"Bogus": "1"}
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], ErrorKind.PARAM_INVALID.value)
        mock_comp.parameters.assert_not_called()

    async def test_safe_set_rollback_on_mismatch(self):
        mock_prj = MagicMock()
        mock_comp = MagicMock()
        mock_comp.range.return_value = (0, 1000)
        mock_comp.parameters.side_effect = [
            {"Tap": "1.00 [pu]"},
            None,
            {"Tap": "1.00 [pu]"},
            None,
        ]
        mock_prj.component.return_value = mock_comp
        self.mock_pscad.project.return_value = mock_prj

        result = await set_component_parameters_safe(
            project_name="case",
            component_id=42,
            parameters={"Tap": "1.05"},
            rollback_on_mismatch=True,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["kind"], ErrorKind.PARAM_INVALID.value)
        kwargs_calls = [c for c in mock_comp.parameters.call_args_list if c.kwargs]
        self.assertEqual(len(kwargs_calls), 2)
        self.assertEqual(kwargs_calls[1].kwargs["parameters"], {"Tap": "1.00 [pu]"})


class TestErrorClassifier(unittest.TestCase):
    def test_timeout_error_is_frozen(self):
        self.assertEqual(classify_exception(asyncio.TimeoutError()), ErrorKind.FROZEN)

    def test_unresponsive_runtime_is_frozen(self):
        e = RuntimeError("PSCAD is unresponsive: COM Error")
        self.assertEqual(classify_exception(e), ErrorKind.FROZEN)

    def test_license_runtime(self):
        e = RuntimeError("PSCAD is not licensed.")
        self.assertEqual(classify_exception(e), ErrorKind.LICENSE)

    def test_connection_lost_runtime(self):
        e = RuntimeError("Connection to PSCAD lost.")
        self.assertEqual(classify_exception(e), ErrorKind.NOT_CONNECTED)

    def test_filenotfound_is_not_found(self):
        self.assertEqual(classify_exception(FileNotFoundError("x")), ErrorKind.NOT_FOUND)

    def test_unclassified_falls_back_to_internal(self):
        self.assertEqual(classify_exception(Exception("totally novel error")), ErrorKind.INTERNAL)


class TestValueEquivalence(unittest.TestCase):
    def test_exact_string_match(self):
        self.assertTrue(values_equivalent("1.05", "1.05"))

    def test_unit_suffix_added_by_pscad(self):
        self.assertTrue(values_equivalent("1.05", "1.05 [pu]"))

    def test_unit_suffix_present_on_both(self):
        self.assertTrue(values_equivalent("230 [kV]", "230 [kV]"))

    def test_numeric_equivalence(self):
        self.assertTrue(values_equivalent("1.05", "1.0500"))

    def test_genuine_mismatch(self):
        self.assertFalse(values_equivalent("1.05", "2.00"))

    def test_none_stored(self):
        self.assertFalse(values_equivalent("1.05", None))


if __name__ == "__main__":
    unittest.main()
