import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchSynchronousMachineCatalogTest(unittest.TestCase):
    def test_database_validates_and_lists_both_machine_types(self):
        database = (
            agent_module.DIgSILENTAgent
            ._load_evemtbench_synchronous_machine_database()
        )
        result = (
            agent_module.DIgSILENTAgent
            .list_evemtbench_synchronous_machine_profiles()
        )

        self.assertEqual(database["schema_version"], 1)
        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 2)
        self.assertEqual(
            [item["machine_type"] for item in result["results"]],
            ["salient_pole", "round_rotor"],
        )
        self.assertEqual(
            result["rated_voltage_rule"][2],
            {"maximum_rated_power_mva": 800.0, "rated_voltage_kv": 21.0},
        )

    def test_filter_returns_only_requested_profile(self):
        result = (
            agent_module.DIgSILENTAgent
            .list_evemtbench_synchronous_machine_profiles("round_rotor")
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(result["returned_count"], 1)
        profile = result["results"][0]
        self.assertEqual(profile["machine_type"], "round_rotor")
        self.assertEqual(
            profile["rated_apparent_power_mva"],
            {"min": 25.0, "max": 1200.0},
        )
        self.assertEqual(
            profile["parameters"]["reactive_power_min_pu"],
            {"value": -0.41},
        )

    def test_filter_rejects_unknown_machine_type(self):
        result = (
            agent_module.DIgSILENTAgent
            .list_evemtbench_synchronous_machine_profiles("induction")
        )

        self.assertFalse(result["success"])
        self.assertIn("salient_pole, round_rotor", result["message"])

    def test_listing_does_not_open_powerfactory(self):
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            side_effect=AssertionError("PowerFactory must not be opened"),
        ):
            result = (
                agent_module.DIgSILENTAgent
                .list_evemtbench_synchronous_machine_profiles("salient_pole")
            )

        self.assertTrue(result["success"], result.get("message"))


class EvEMTBenchSynchronousMachineCreatorTest(unittest.TestCase):
    def network(self, voltage=10.5, with_type_folder=True):
        equipment = FakeObject(
            None,
            "IntPrjfolder",
            "Equipment Type Library",
        )
        if with_type_folder:
            equipment.CreateObject("IntPrjfolder", "Generator Types")
        grid = FakeObject(None, "ElmNet", "Grid")
        bus = grid.CreateObject("ElmTerm", "Generator Bus")
        bus.SetAttribute("uknom", voltage)
        return equipment, grid, bus, FakeApplication(equipment, grid)

    @staticmethod
    def machine_types(equipment):
        folders = equipment["IntPrjfolder"]
        return folders[0]["TypSym"] if folders else []

    def call(self, app, **kwargs):
        arguments = {
            "machine_type": "round_rotor",
            "rated_power_mva": 100.0,
            "machine_name": "Research Generator",
            "type_name": "Research Generator Type",
            "bus_name": "Generator Bus",
            "seed": 42,
            "active_power_mw": 60.0,
            "reactive_power_mvar": 5.0,
            "open_digsilent": False,
        }
        arguments.update(kwargs)
        with patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ):
            return (
                agent_module.DIgSILENTAgent
                .create_evemtbench_synchronous_machine(**arguments)
            )

    def test_preview_is_deterministic_and_respects_dependencies(self):
        equipment, grid, bus, app = self.network()

        first = self.call(app)
        second = self.call(app)

        self.assertTrue(first["success"], first.get("message"))
        self.assertFalse(first["applied"])
        self.assertEqual(first["item"], second["item"])
        self.assertEqual(self.machine_types(equipment), [])
        self.assertEqual(grid["ElmSym"], [])
        self.assertEqual(bus["StaCubic"], [])
        self.assertEqual(
            first["confirmation_required"],
            "CREATE Research Generator WITH Research Generator Type "
            "round_rotor 100MVA 10.5kV seed=42 grid=<active> "
            "bus=Generator Bus p=60MW q=5Mvar out_of_service=0",
        )
        values = first["item"]["parameters"]
        self.assertEqual(values["rated_voltage_kv"], 10.5)
        self.assertGreaterEqual(
            values["xq_subtransient_pu"],
            values["xd_subtransient_pu"],
        )
        self.assertGreaterEqual(
            values["xq_transient_pu"],
            1.01 * values["xq_subtransient_pu"] - 1e-6,
        )
        self.assertGreaterEqual(
            values["xd_synchronous_pu"],
            1.01 * values["xd_transient_pu"] - 1e-6,
        )
        self.assertGreaterEqual(
            values["xq_synchronous_pu"],
            1.01 * values["xq_transient_pu"] - 1e-6,
        )
        self.assertGreaterEqual(
            values["saturation_factor_1_2_pu"],
            values["saturation_factor_1_0_pu"],
        )
        inputs = first["item"]["powerfactory_attributes"]
        derived = first["item"]["powerfactory_derived_attributes"]
        for actual, expected in (
            (inputs["tds0"] * values["xd_transient_pu"]
             / values["xd_synchronous_pu"], derived["tds"]),
            (inputs["tqs0"] * values["xq_transient_pu"]
             / values["xq_synchronous_pu"], derived["tqs"]),
            (inputs["tdss0"] * values["xd_subtransient_pu"]
             / values["xd_transient_pu"], derived["tdss"]),
            (inputs["tqss0"] * values["xq_subtransient_pu"]
             / values["xq_transient_pu"], derived["tqss"]),
        ):
            self.assertAlmostEqual(actual, expected)

    def test_confirmation_creates_type_and_connected_machine(self):
        equipment, grid, bus, app = self.network()
        preview = self.call(app, out_of_service=True)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
            out_of_service=True,
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["type_created"])
        self.assertTrue(result["machine_created"])
        created_type = self.machine_types(equipment)[0]
        machine = grid["ElmSym"][0]
        self.assertEqual(created_type.write_count, 3)
        self.assertEqual(created_type.GetAttribute("iturbo"), 1)
        self.assertEqual(created_type.GetAttribute("sgn"), 100.0)
        self.assertEqual(created_type.GetAttribute("ugn"), 10.5)
        for attribute, expected in (
            result["item"]["powerfactory_derived_attributes"].items()
        ):
            self.assertAlmostEqual(
                result["retained_derived_attributes"][attribute],
                expected,
            )
        self.assertIs(machine.GetAttribute("typ_id"), created_type)
        self.assertEqual(machine.GetAttribute("pgini"), 60.0)
        self.assertEqual(machine.GetAttribute("qgini"), 5.0)
        self.assertEqual(machine.GetAttribute("outserv"), 1)
        self.assertIs(machine.GetAttribute("bus1"), bus["StaCubic"][0])
        switch = bus["StaCubic"][0]["StaSwitch"][0]
        self.assertEqual(switch.GetAttribute("aUsage"), "cbk")
        self.assertEqual(switch.GetAttribute("on_off"), 1)
        for attribute, expected in (
            result["item"]["powerfactory_attributes"].items()
        ):
            actual = created_type.GetAttribute(attribute)
            if isinstance(expected, float):
                self.assertAlmostEqual(actual, expected)
            else:
                self.assertEqual(actual, expected)

    def test_creates_generator_types_folder_for_greenfield_project(self):
        equipment, _, _, app = self.network(with_type_folder=False)
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
        )

        self.assertTrue(result["success"], result.get("message"))
        self.assertEqual(
            equipment["IntPrjfolder"][0].GetAttribute("loc_name"),
            "Generator Types",
        )
        self.assertEqual(len(self.machine_types(equipment)), 1)

    def test_salient_pole_remains_catalog_only(self):
        _, _, _, app = self.network()

        result = self.call(app, machine_type="salient_pole")

        self.assertFalse(result["success"])
        self.assertIn("does not provide xq transient data", result["message"])

    def test_rejects_wrong_bus_voltage_and_invalid_operating_point(self):
        equipment, grid, _, app = self.network(voltage=21.0)

        wrong_voltage = self.call(app)
        too_large = self.call(app, active_power_mw=100.0, reactive_power_mvar=1.0)
        too_reactive = self.call(app, reactive_power_mvar=49.0)

        self.assertFalse(wrong_voltage["success"])
        self.assertIn("expected 10.5 kV", wrong_voltage["message"])
        self.assertFalse(too_large["success"])
        self.assertIn("exceeds rated_power_mva", too_large["message"])
        self.assertFalse(too_reactive["success"])
        self.assertIn("must be between -41 and 48", too_reactive["message"])
        self.assertEqual(self.machine_types(equipment), [])
        self.assertEqual(grid["ElmSym"], [])

    def test_element_failure_rolls_back_type_and_connections(self):
        equipment, grid, bus, app = self.network()
        grid.reject_attribute = "typ_id"
        preview = self.call(app)

        result = self.call(
            app,
            confirmation=preview["confirmation_required"],
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertFalse(result["type_created"])
        self.assertEqual(self.machine_types(equipment), [])
        self.assertEqual(grid["ElmSym"], [])
        self.assertEqual(bus["StaCubic"], [])

    def test_confirmation_is_bound_to_machine_bus_operating_point_and_state(self):
        equipment, grid, bus, app = self.network()
        alternate_bus = grid.CreateObject("ElmTerm", "Alternate Generator Bus")
        alternate_bus.SetAttribute("uknom", 10.5)
        preview = self.call(app)

        changed_requests = (
            {"machine_name": "Renamed Generator"},
            {"bus_name": "Alternate Generator Bus"},
            {"seed": 43},
            {"active_power_mw": 61.0},
            {"reactive_power_mvar": 6.0},
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
                self.assertEqual(self.machine_types(equipment), [])
                self.assertEqual(grid["ElmSym"], [])
                self.assertEqual(bus["StaCubic"], [])
                self.assertEqual(alternate_bus["StaCubic"], [])


if __name__ == "__main__":
    unittest.main()
