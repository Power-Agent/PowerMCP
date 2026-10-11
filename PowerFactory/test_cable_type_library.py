import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchCableTest(unittest.TestCase):
    def network(self, voltage=20.0):
        folder = FakeObject(None, "IntPrjfolder", "Equipment Type Library")
        folder.CreateObject("IntPrjfolder", "Line Types")
        grid = FakeObject(None, "ElmNet", "Grid")
        first_bus = grid.CreateObject("ElmTerm", "Cable Bus A")
        second_bus = grid.CreateObject("ElmTerm", "Cable Bus B")
        first_bus.SetAttribute("uknom", voltage)
        second_bus.SetAttribute("uknom", voltage)
        return folder, grid, first_bus, second_bus, FakeApplication(folder, grid)

    @staticmethod
    def cable_types(folder):
        return folder["IntPrjfolder"][0]["TypLne"]

    def call(self, app, **kwargs):
        arguments = {
            "nominal_frequency_hz": 50.0,
            "rated_current_ka": 0.4,
            "profile": "p50",
            "length_km": 2.0,
            "cable_name": "Research Cable",
            "type_name": "Research Cable Type",
            "bus1_name": "Cable Bus A",
            "bus2_name": "Cable Bus B",
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return agent_module.DIgSILENTAgent.create_evemtbench_cable(
                **arguments
            )

    def test_database_validates_and_filters_profiles(self):
        database = agent_module.DIgSILENTAgent._load_evemtbench_cable_database()
        result = agent_module.DIgSILENTAgent.list_evemtbench_cable_profiles(
            "p50"
        )

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        cable_class = result["results"][0]
        self.assertEqual(cable_class["voltage_class"], "20")
        self.assertEqual(list(cable_class["electrical_profiles"]), ["p50"])
        self.assertEqual(
            cable_class["electrical_profiles"]["p50"]["c1_nf_per_km"],
            247.06,
        )
        self.assertEqual(result["construction"]["insulation_thickness_mm"], 5.5)

    def test_preview_creates_nothing_and_converts_capacitance(self):
        folder, grid, first_bus, second_bus, app = self.network()

        result = self.call(app)

        self.assertTrue(result["success"], result.get("message"))
        self.assertFalse(result["applied"])
        self.assertFalse(result["type_created"])
        self.assertFalse(result["cable_created"])
        self.assertEqual(self.cable_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])
        self.assertEqual(first_bus["StaCubic"], [])
        self.assertEqual(second_bus["StaCubic"], [])
        self.assertEqual(
            result["confirmation_required"],
            "CREATE Research Cable WITH Research Cable Type 20kV p50 "
            "2km 0.4kA 50Hz",
        )
        attributes = result["item"]["powerfactory_attributes"]
        self.assertEqual(attributes["rline"], 0.2125)
        self.assertEqual(attributes["xline"], 0.1411)
        self.assertAlmostEqual(attributes["cline"], 0.24706)
        self.assertEqual(attributes["rline0"], 0.7775)
        self.assertEqual(attributes["xline0"], 0.2661)
        self.assertAlmostEqual(attributes["cline0"], 0.24706)

    def test_confirmation_creates_type_and_connected_cable(self):
        folder, grid, first_bus, second_bus, app = self.network()
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["type_created"])
        self.assertTrue(result["cable_created"])
        created_type = self.cable_types(folder)[0]
        cable = grid["ElmLne"][0]
        self.assertIs(cable.GetAttribute("typ_id"), created_type)
        self.assertEqual(cable.GetAttribute("dline"), 2.0)
        self.assertEqual(cable.GetAttribute("outserv"), 1)
        self.assertIs(cable.GetAttribute("bus1"), first_bus["StaCubic"][0])
        self.assertIs(cable.GetAttribute("bus2"), second_bus["StaCubic"][0])
        for attribute, expected in result["item"][
            "powerfactory_attributes"
        ].items():
            self.assertAlmostEqual(created_type.GetAttribute(attribute), expected)
        self.assertEqual(created_type.write_count, 2)

    def test_validation_rejects_unsupported_requests(self):
        _, _, _, _, app = self.network()

        bad_profile = self.call(app, profile="p75")
        bad_length = self.call(app, length_km=4.0)
        bad_frequency = self.call(app, nominal_frequency_hz=55.0)

        self.assertFalse(bad_profile["success"])
        self.assertIn("profile must be one of", bad_profile["message"])
        self.assertFalse(bad_length["success"])
        self.assertIn("between 0.5 and 3.75", bad_length["message"])
        self.assertFalse(bad_frequency["success"])
        self.assertIn("must be 50 or 60", bad_frequency["message"])

    def test_bus_voltage_mismatch_is_rejected_in_preview(self):
        folder, grid, _, _, app = self.network(voltage=110.0)

        result = self.call(app)

        self.assertFalse(result["success"])
        self.assertIn("expected 20 kV", result["message"])
        self.assertEqual(self.cable_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])

    def test_element_failure_rolls_back_type_and_connections(self):
        folder, grid, first_bus, second_bus, app = self.network()
        grid.reject_attribute = "typ_id"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertFalse(result["cable_created"])
        self.assertEqual(self.cable_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])
        self.assertEqual(first_bus["StaCubic"], [])
        self.assertEqual(second_bus["StaCubic"], [])


if __name__ == "__main__":
    unittest.main()
