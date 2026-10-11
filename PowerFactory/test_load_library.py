import math
import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchLoadTest(unittest.TestCase):
    def network(self, voltage=20.0):
        equipment = FakeObject(None, "IntPrjfolder", "Equipment Type Library")
        grid = FakeObject(None, "ElmNet", "Grid")
        bus = grid.CreateObject("ElmTerm", "Load Bus")
        bus.SetAttribute("uknom", voltage)
        return grid, bus, FakeApplication(equipment, grid)

    def call(self, app, **kwargs):
        arguments = {
            "voltage_kv": 20.0,
            "load_name": "Research Load",
            "bus_name": "Load Bus",
            "seed": 42,
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return agent_module.DIgSILENTAgent.create_evemtbench_load(
                **arguments
            )

    def test_database_validates_and_filters_voltage_classes(self):
        database = agent_module.DIgSILENTAgent._load_evemtbench_load_database()
        result = agent_module.DIgSILENTAgent.list_evemtbench_load_profiles(
            345.0
        )

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["results"][0]["voltage_class"], "345")
        self.assertEqual(
            result["results"][0]["active_power_mw"],
            {"min": 9.0, "max": 326.0},
        )

    def test_twenty_kv_preview_is_reproducible_and_physically_consistent(self):
        grid, bus, app = self.network()

        first = self.call(app)
        second = self.call(app)

        self.assertTrue(first["success"], first.get("message"))
        self.assertFalse(first["applied"])
        self.assertFalse(first["load_created"])
        self.assertEqual(first["item"], second["item"])
        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(bus["StaCubic"], [])
        parameters = first["item"]["parameters"]
        apparent = math.hypot(
            parameters["active_power_mw"],
            parameters["reactive_power_mvar"],
        )
        self.assertAlmostEqual(
            apparent,
            parameters["apparent_power_mva"],
            places=5,
        )
        self.assertGreaterEqual(apparent, 0.1)
        self.assertLessEqual(apparent, 1.6)
        if parameters["power_factor_mode"] == "inductive":
            self.assertGreaterEqual(parameters["power_factor"], 0.8)
            self.assertGreaterEqual(parameters["reactive_power_mvar"], 0.0)
        else:
            self.assertGreaterEqual(parameters["power_factor"], 0.95)
            self.assertLess(parameters["reactive_power_mvar"], 0.0)

    def test_confirmation_creates_connected_load(self):
        grid, bus, app = self.network(voltage=110.0)
        preview = self.call(app, voltage_kv=110.0)

        result = self.call(
            app,
            voltage_kv=110.0,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["load_created"])
        load = grid["ElmLod"][0]
        self.assertIs(load.GetAttribute("bus1"), bus["StaCubic"][0])
        self.assertEqual(load.GetAttribute("outserv"), 1)
        for attribute, expected in preview["item"][
            "powerfactory_attributes"
        ].items():
            self.assertEqual(load.GetAttribute(attribute), expected)

    def test_validation_rejects_unsupported_or_mismatched_voltage(self):
        _, _, app = self.network()
        unsupported = self.call(app, voltage_kv=30.0)
        _, _, mismatch_app = self.network(voltage=110.0)
        mismatch = self.call(mismatch_app)

        self.assertFalse(unsupported["success"])
        self.assertIn("must be one of", unsupported["message"])
        self.assertFalse(mismatch["success"])
        self.assertIn("is 110 kV; expected 20 kV", mismatch["message"])

    def test_wrong_confirmation_creates_nothing(self):
        grid, bus, app = self.network()

        result = self.call(app, confirmation="CREATE SOMETHING ELSE")

        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(bus["StaCubic"], [])

    def test_failed_attribute_verification_rolls_back_connections(self):
        grid, bus, app = self.network()
        grid.reject_attribute = "plini"
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(bus["StaCubic"], [])

    def test_confirmation_is_bound_to_load_name_bus_seed_and_state(self):
        grid, bus, app = self.network()
        alternate_bus = grid.CreateObject("ElmTerm", "Other Load Bus")
        alternate_bus.SetAttribute("uknom", 20.0)
        preview = self.call(app)

        changed_requests = (
            {"load_name": "Renamed Load"},
            {"bus_name": "Other Load Bus"},
            {"seed": 43},
            {"out_of_service": True},
        )
        for changes in changed_requests:
            with self.subTest(changes=changes):
                result = self.call(
                    app,
                    confirmation=preview["confirmation_required"],
                    **changes,
                )
                self.assertFalse(result["success"])
                self.assertIn("confirmation must exactly match", result["message"])
                self.assertEqual(grid["ElmLod"], [])
                self.assertEqual(bus["StaCubic"], [])
                self.assertEqual(alternate_bus["StaCubic"], [])


if __name__ == "__main__":
    unittest.main()
