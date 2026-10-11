import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchExternalGridTest(unittest.TestCase):
    def network(self, voltage=110.0):
        equipment = FakeObject(None, "IntPrjfolder", "Equipment Type Library")
        grid = FakeObject(None, "ElmNet", "Grid")
        bus = grid.CreateObject("ElmTerm", "Source Bus")
        bus.SetAttribute("uknom", voltage)
        return grid, bus, FakeApplication(equipment, grid)

    def call(self, app, **kwargs):
        arguments = {
            "voltage_kv": 110.0,
            "external_grid_name": "Research External Grid",
            "bus_name": "Source Bus",
            "seed": 42,
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return agent_module.DIgSILENTAgent.create_evemtbench_external_grid(
                **arguments
            )

    def test_database_validates_and_filters_voltage_classes(self):
        database = (
            agent_module.DIgSILENTAgent
            ._load_evemtbench_external_grid_database()
        )
        result = (
            agent_module.DIgSILENTAgent
            .list_evemtbench_external_grid_profiles(345.0)
        )

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["results"][0]["voltage_class"], "380/345")
        self.assertEqual(
            result["results"][0]["short_circuit_power_mva"],
            {"min": 10000.0, "max": 53000.0},
        )

    def test_preview_is_reproducible_and_creates_nothing(self):
        grid, bus, app = self.network()

        first = self.call(app)
        second = self.call(app)

        self.assertTrue(first["success"], first.get("message"))
        self.assertFalse(first["applied"])
        self.assertFalse(first["external_grid_created"])
        self.assertEqual(first["item"], second["item"])
        self.assertEqual(grid["ElmXnet"], [])
        self.assertEqual(bus["StaCubic"], [])
        self.assertEqual(
            first["confirmation_required"],
            "CREATE Research External Grid AT Source Bus 110kV seed=42",
        )
        parameters = first["item"]["parameters"]
        self.assertGreaterEqual(parameters["short_circuit_power_mva"], 800.0)
        self.assertLessEqual(parameters["short_circuit_power_mva"], 8000.0)
        self.assertGreaterEqual(parameters["initial_phase_angle_deg"], -180.0)
        self.assertLessEqual(parameters["initial_phase_angle_deg"], 180.0)

    def test_confirmation_creates_connected_slack_external_grid(self):
        grid, bus, app = self.network()
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["external_grid_created"])
        external_grid = grid["ElmXnet"][0]
        self.assertIs(external_grid.GetAttribute("bus1"), bus["StaCubic"][0])
        self.assertEqual(external_grid.GetAttribute("outserv"), 1)
        for attribute, expected in preview["item"][
            "powerfactory_attributes"
        ].items():
            self.assertEqual(external_grid.GetAttribute(attribute), expected)
        switch = bus["StaCubic"][0]["StaSwitch"][0]
        self.assertEqual(switch.GetAttribute("aUsage"), "cbk")
        self.assertEqual(switch.GetAttribute("on_off"), 1)

    def test_validation_rejects_unsupported_or_mismatched_voltage(self):
        _, _, app = self.network()
        unsupported = self.call(app, voltage_kv=220.0)
        _, _, mismatch_app = self.network(voltage=20.0)
        mismatch = self.call(mismatch_app)

        self.assertFalse(unsupported["success"])
        self.assertIn("must be one of", unsupported["message"])
        self.assertFalse(mismatch["success"])
        self.assertIn("is 20 kV; expected 110 kV", mismatch["message"])

    def test_wrong_confirmation_creates_nothing(self):
        grid, bus, app = self.network()

        result = self.call(app, confirmation="CREATE SOMETHING ELSE")

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(grid["ElmXnet"], [])
        self.assertEqual(bus["StaCubic"], [])

    def test_failed_attribute_verification_rolls_back_connections(self):
        grid, bus, app = self.network()
        grid.reject_attribute = "snss"
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(grid["ElmXnet"], [])
        self.assertEqual(bus["StaCubic"], [])


if __name__ == "__main__":
    unittest.main()
