import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchLineTest(unittest.TestCase):
    def network(self, voltage=110.0, with_type_folder=True):
        folder = FakeObject(None, "IntPrjfolder", "Equipment Type Library")
        if with_type_folder:
            folder.CreateObject("IntPrjfolder", "Line Types")
        grid = FakeObject(None, "ElmNet", "Grid")
        first_bus = grid.CreateObject("ElmTerm", "Bus A")
        second_bus = grid.CreateObject("ElmTerm", "Bus B")
        first_bus.SetAttribute("uknom", voltage)
        second_bus.SetAttribute("uknom", voltage)
        return folder, grid, first_bus, second_bus, FakeApplication(folder, grid)

    @staticmethod
    def line_types(folder):
        type_folders = folder["IntPrjfolder"]
        return type_folders[0]["TypLne"] if type_folders else []

    def call(self, app, **kwargs):
        arguments = {
            "voltage_kv": 110.0,
            "nominal_frequency_hz": 50.0,
            "rated_current_ka": 1.0,
            "profile": "p50",
            "length_km": 10.0,
            "line_name": "Research Line",
            "type_name": "Research Line Type",
            "bus1_name": "Bus A",
            "bus2_name": "Bus B",
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return agent_module.DIgSILENTAgent.create_evemtbench_line(
                **arguments
            )

    def test_database_validates_and_filters_profiles(self):
        database = agent_module.DIgSILENTAgent._load_evemtbench_line_database()
        result = agent_module.DIgSILENTAgent.list_evemtbench_line_profiles(
            110.0,
            "p50",
        )

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        line_class = result["results"][0]
        self.assertEqual(line_class["voltage_class"], "110")
        self.assertEqual(list(line_class["electrical_profiles"]), ["p50"])
        self.assertEqual(
            line_class["electrical_profiles"]["p50"]["c1_nf_per_km"],
            12.58,
        )

    def test_preview_creates_nothing_and_converts_capacitance(self):
        folder, grid, first_bus, second_bus, app = self.network()

        result = self.call(app)

        self.assertTrue(result["success"], result.get("message"))
        self.assertFalse(result["applied"])
        self.assertFalse(result["type_created"])
        self.assertFalse(result["line_created"])
        self.assertEqual(self.line_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])
        self.assertEqual(first_bus["StaCubic"], [])
        self.assertEqual(second_bus["StaCubic"], [])
        self.assertTrue(
            result["confirmation_required"].startswith(
                "CREATE Research Line WITH Research Line Type 110kV p50 "
                "10km 1kA 50Hz grid=<active> "
                "buses=Bus A->Bus B out_of_service=0"
            )
        )
        self.assertRegex(result["confirmation_required"], r" plan=[0-9a-f]{64}$")
        attributes = result["item"]["powerfactory_attributes"]
        self.assertEqual(attributes["rline"], 0.06)
        self.assertEqual(attributes["xline"], 0.29)
        self.assertAlmostEqual(attributes["cline"], 0.01258)
        self.assertEqual(attributes["rline0"], 0.31)
        self.assertEqual(attributes["xline0"], 1.07)
        self.assertAlmostEqual(attributes["cline0"], 0.00559)

    def test_confirmation_creates_type_and_connected_line(self):
        folder, grid, first_bus, second_bus, app = self.network()
        preview = self.call(app, out_of_service=True)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["applied"])
        self.assertTrue(result["type_created"])
        self.assertTrue(result["line_created"])
        created_type = self.line_types(folder)[0]
        line = grid["ElmLne"][0]
        self.assertIs(line.GetAttribute("typ_id"), created_type)
        self.assertEqual(line.GetAttribute("dline"), 10.0)
        self.assertEqual(line.GetAttribute("outserv"), 1)
        self.assertIs(line.GetAttribute("bus1"), first_bus["StaCubic"][0])
        self.assertIs(line.GetAttribute("bus2"), second_bus["StaCubic"][0])
        for bus in (first_bus, second_bus):
            switch = bus["StaCubic"][0]["StaSwitch"][0]
            self.assertEqual(switch.GetAttribute("aUsage"), "cbk")
            self.assertEqual(switch.GetAttribute("on_off"), 1)
        for attribute, expected in result["item"][
            "powerfactory_attributes"
        ].items():
            self.assertAlmostEqual(created_type.GetAttribute(attribute), expected)
        self.assertEqual(created_type.write_count, 2)

    def test_creates_line_types_folder_for_greenfield_project(self):
        folder, _, _, _, app = self.network(with_type_folder=False)
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(
            folder["IntPrjfolder"][0].GetAttribute("loc_name"),
            "Line Types",
        )
        self.assertEqual(len(self.line_types(folder)), 1)

    def test_validation_rejects_unsupported_requests(self):
        _, _, _, _, app = self.network()

        bad_profile = self.call(app, profile="p75")
        bad_length = self.call(app, length_km=40.0)
        bad_frequency = self.call(app, nominal_frequency_hz=55.0)
        bad_voltage = self.call(app, voltage_kv=220.0)

        self.assertFalse(bad_profile["success"])
        self.assertIn("profile must be one of", bad_profile["message"])
        self.assertFalse(bad_length["success"])
        self.assertIn("between 1 and 32", bad_length["message"])
        self.assertFalse(bad_frequency["success"])
        self.assertIn("must be 50 or 60", bad_frequency["message"])
        self.assertFalse(bad_voltage["success"])
        self.assertIn("voltage_kv must be one of", bad_voltage["message"])

    def test_bus_voltage_mismatch_is_rejected_in_preview(self):
        folder, grid, _, _, app = self.network(voltage=20.0)

        result = self.call(app)

        self.assertFalse(result["success"])
        self.assertIn("expected 110 kV", result["message"])
        self.assertEqual(self.line_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])

    def test_element_failure_rolls_back_type_and_connections(self):
        folder, grid, first_bus, second_bus, app = self.network()
        grid.reject_attribute = "typ_id"
        preview = self.call(app)

        result = self.call(app, confirmation=preview["confirmation_required"])

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(self.line_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])
        self.assertEqual(first_bus["StaCubic"], [])
        self.assertEqual(second_bus["StaCubic"], [])

    def test_confirmation_distinguishes_float_values_hidden_by_general_format(self):
        folder, grid, first_bus, second_bus, app = self.network()
        preview = self.call(app, length_km=1.0000001)
        changed_preview = self.call(app, length_km=1.0000002)
        self.assertTrue(preview["success"], preview.get("message"))
        self.assertEqual(
            preview["confirmation_required"].split(" plan=")[0],
            changed_preview["confirmation_required"].split(" plan=")[0],
        )
        self.assertNotEqual(
            preview["confirmation_required"],
            changed_preview["confirmation_required"],
        )
        changed = self.call(
            app,
            length_km=1.0000002,
            confirmation=preview["confirmation_required"],
        )
        self.assertFalse(changed["success"])
        self.assertIn("confirmation must exactly match", changed["message"])
        self.assertEqual(self.line_types(folder), [])
        self.assertEqual(grid["ElmLne"], [])
        self.assertEqual(first_bus["StaCubic"], [])
        self.assertEqual(second_bus["StaCubic"], [])

    def test_confirmation_is_bound_to_profile_buses_and_line_options(self):
        folder, grid, first_bus, second_bus, app = self.network()
        alternate_bus = grid.CreateObject("ElmTerm", "Bus C")
        alternate_bus.SetAttribute("uknom", 110.0)
        preview = self.call(app)

        changed_requests = (
            {"profile": "p95"},
            {"bus2_name": "Bus C"},
            {"line_name": "Renamed Line"},
            {"length_km": 11.0},
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
                self.assertEqual(self.line_types(folder), [])
                self.assertEqual(grid["ElmLne"], [])
                self.assertEqual(first_bus["StaCubic"], [])
                self.assertEqual(second_bus["StaCubic"], [])


if __name__ == "__main__":
    unittest.main()
