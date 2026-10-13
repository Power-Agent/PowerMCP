import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeObject


class BootstrapApplication:
    def __init__(self, project):
        self.project = project
        self.active_grids = set()
        self.activation_code = 0

    def GetActiveProject(self):
        return self.project

    def GetActiveStudyCase(self):
        return self.project

    def GetCalcRelevantObjects(self, query):
        if query != "*.ElmNet":
            return []
        return [
            grid
            for grid in self.project.GetContents("*.ElmNet", 1)
            if grid.GetFullName() in self.active_grids
        ]

    def activate(self, grid):
        if self.activation_code not in (None, 0):
            return self.activation_code
        self.active_grids.add(grid.GetFullName())
        return self.activation_code

    def deactivate(self, grid):
        self.active_grids.discard(grid.GetFullName())
        return 0


class GridBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.project = FakeObject(None, "IntPrj", "Project")
        self.app = BootstrapApplication(self.project)

    def call(self, **kwargs):
        arguments = {
            "grid_name": "Research Grid",
            "nominal_frequency_hz": 50.0,
            "buses": [
                {
                    "name": "HV Bus",
                    "nominal_voltage_kv": 110.0,
                },
                {
                    "name": "MV Bus",
                    "nominal_voltage_kv": 20.0,
                    "out_of_service": True,
                },
            ],
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with (
            patch.object(
                agent_module.DIgSILENTAgent,
                "_get_application",
                return_value=self.app,
            ),
            patch.object(
                FakeObject,
                "Activate",
                lambda grid: self.app.activate(grid),
                create=True,
            ),
            patch.object(
                FakeObject,
                "Deactivate",
                lambda grid: self.app.deactivate(grid),
                create=True,
            ),
        ):
            return agent_module.DIgSILENTAgent.create_grid_with_buses(
                **arguments
            )

    def create_existing_grid(self):
        model = self.project.CreateObject("IntPrjfolder", "Network Model")
        data = model.CreateObject("IntPrjfolder", "Network Data")
        grid = data.CreateObject("ElmNet", "Research Grid")
        grid.SetAttribute("frnom", 50.0)
        self.app.activate(grid)
        return grid

    def test_preview_creates_nothing(self):
        result = self.call()

        self.assertTrue(result["success"], result.get("message"))
        self.assertFalse(result["applied"])
        self.assertFalse(result["grid_created"])
        self.assertEqual(result["buses_created"], 0)
        self.assertTrue(result["grid_will_be_created"])
        self.assertRegex(
            result["confirmation_required"],
            r"^CREATE GRID Research Grid 50Hz WITH 2 BUSES plan=[0-9a-f]{64}$",
        )
        self.assertEqual(self.project["IntPrjfolder"], [])

    def test_active_study_case_is_required(self):
        self.app.GetActiveStudyCase = lambda: None

        result = self.call()

        self.assertFalse(result["success"])
        self.assertIn("No PowerFactory study case is active", result["message"])
        self.assertEqual(self.project["IntPrjfolder"], [])

    def test_confirmation_is_bound_to_the_exact_bus_plan(self):
        preview = self.call()

        result = self.call(
            buses=[
                {"name": "HV Bus", "nominal_voltage_kv": 110.0},
                {"name": "Other Bus", "nominal_voltage_kv": 20.0},
            ],
            confirmation=preview["confirmation_required"],
        )

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(self.project["IntPrjfolder"], [])

    def test_confirmation_is_bound_to_the_active_project(self):
        preview = self.call()
        other_project = FakeObject(None, "IntPrj", "Other Project")
        self.app.project = other_project

        result = self.call(confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(other_project["IntPrjfolder"], [])

    def test_confirmation_is_bound_to_grid_create_or_reuse_decision(self):
        preview = self.call()
        grid = self.create_existing_grid()
        self.app.deactivate(grid)

        result = self.call(confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(grid["ElmTerm"], [])
        self.assertNotIn(grid.GetFullName(), self.app.active_grids)

    def test_confirmation_is_bound_to_destination_folder_plan(self):
        preview = self.call()
        model = self.project.CreateObject("IntPrjfolder", "Network Model")
        model.CreateObject("IntPrjfolder", "Network Data")

        result = self.call(confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(self.project.GetContents("*.ElmNet", 1), [])
        self.assertEqual(
            self.project["IntPrjfolder"][0]["IntPrjfolder"][0]["ElmNet"],
            [],
        )

    def test_confirmation_creates_folder_grid_and_buses(self):
        preview = self.call()

        result = self.call(
            confirmation=preview["confirmation_required"],
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["grid_created"])
        self.assertTrue(result["grid_activated"])
        self.assertEqual(result["buses_created"], 2)
        model = self.project["IntPrjfolder"][0]
        data = model["IntPrjfolder"][0]
        grid = data["ElmNet"][0]
        self.assertEqual(grid.GetAttribute("frnom"), 50.0)
        self.assertEqual(
            [bus.GetAttribute("loc_name") for bus in grid["ElmTerm"]],
            ["HV Bus", "MV Bus"],
        )
        self.assertEqual(grid["ElmTerm"][0].GetAttribute("uknom"), 110.0)
        self.assertEqual(grid["ElmTerm"][0].GetAttribute("outserv"), 0)
        self.assertEqual(grid["ElmTerm"][1].GetAttribute("uknom"), 20.0)
        self.assertEqual(grid["ElmTerm"][1].GetAttribute("outserv"), 1)
        self.assertEqual(self.app.GetCalcRelevantObjects("*.ElmNet"), [grid])

    def test_existing_inactive_grid_is_activated(self):
        grid = self.create_existing_grid()
        self.app.deactivate(grid)
        for name, voltage, outserv in (
            ("HV Bus", 110.0, 0),
            ("MV Bus", 20.0, 1),
        ):
            bus = grid.CreateObject("ElmTerm", name)
            bus.SetAttribute("uknom", voltage)
            bus.SetAttribute("outserv", outserv)

        preview = self.call()
        result = self.call(confirmation=preview["confirmation_required"])

        self.assertTrue(preview["grid_will_be_activated"])
        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertFalse(result["grid_created"])
        self.assertTrue(result["grid_activated"])
        self.assertEqual(result["buses_created"], 0)
        self.assertEqual(self.app.GetCalcRelevantObjects("*.ElmNet"), [grid])

    def test_existing_grid_and_matching_bus_are_reused(self):
        grid = self.create_existing_grid()
        bus = grid.CreateObject("ElmTerm", "HV Bus")
        bus.SetAttribute("uknom", 110.0)
        preview = self.call()

        result = self.call(
            confirmation=preview["confirmation_required"],
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertFalse(result["grid_created"])
        self.assertEqual(result["buses_created"], 1)
        self.assertEqual(len(result["reused_buses"]), 1)
        self.assertEqual(len(grid["ElmTerm"]), 2)
        self.assertIs(grid["ElmTerm"][0], bus)

        # Applying the plan changes its resolved state: the previously
        # pending MV Bus is now present, so the original token must be stale.
        repeated_with_stale_confirmation = self.call(
            confirmation=preview["confirmation_required"],
        )
        self.assertFalse(repeated_with_stale_confirmation["success"])
        self.assertIn(
            "confirmation must exactly match",
            repeated_with_stale_confirmation["message"],
        )
        self.assertEqual(len(grid["ElmTerm"]), 2)

        # A fresh preview/token for the now-complete grid is valid and is a
        # safe no-op because the grid and both requested buses already exist.
        refreshed_preview = self.call()
        repeated = self.call(
            confirmation=refreshed_preview["confirmation_required"],
        )
        self.assertTrue(repeated["success"], repeated.get("message"))
        self.assertFalse(repeated["applied"])
        self.assertEqual(len(grid["ElmTerm"]), 2)

    def test_existing_values_must_match(self):
        grid = self.create_existing_grid()
        bus = grid.CreateObject("ElmTerm", "HV Bus")
        bus.SetAttribute("uknom", 20.0)

        result = self.call()

        self.assertFalse(result["success"])
        self.assertIn("is 20 kV; expected 110 kV", result["message"])
        self.assertEqual(len(grid["ElmTerm"]), 1)

    def test_validation_rejects_ambiguous_bus_definitions(self):
        duplicate = self.call(buses=[
            {"name": "Bus A", "nominal_voltage_kv": 110.0},
            {"name": "bus a", "nominal_voltage_kv": 110.0},
        ])
        bad_flag = self.call(buses=[{
            "name": "Bus A",
            "nominal_voltage_kv": 110.0,
            "out_of_service": "false",
        }])

        self.assertFalse(duplicate["success"])
        self.assertIn("Duplicate bus name", duplicate["message"])
        self.assertFalse(bad_flag["success"])
        self.assertIn("must be a boolean", bad_flag["message"])
        self.assertEqual(self.project["IntPrjfolder"], [])

    def test_failed_bus_verification_rolls_back_every_new_object(self):
        self.project.reject_attribute = "uknom"
        preview = self.call()

        result = self.call(
            confirmation=preview["confirmation_required"],
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["remaining_objects"], [])
        self.assertEqual(self.project["IntPrjfolder"], [])

    def test_failed_grid_activation_rolls_back_every_new_object(self):
        self.app.activation_code = 1
        preview = self.call()

        result = self.call(confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertIn("Could not activate grid", result["message"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["remaining_objects"], [])
        self.assertEqual(self.project["IntPrjfolder"], [])


if __name__ == "__main__":
    unittest.main()
