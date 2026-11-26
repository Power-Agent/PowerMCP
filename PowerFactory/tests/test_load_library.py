import copy
import math
import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module
from test_transformer_type_library import FakeApplication, FakeObject


class EvEMTBenchLoadTest(unittest.TestCase):
    def test_zip_sampling_is_reproducible_bounded_and_preserves_default_power(self):
        agent = agent_module.DIgSILENTAgent
        specs = agent._load_evemtbench_load_database()["catalog_only"]["load_model_coefficients"]
        for voltage in (20.0, 110.0, 345.0):
            for seed in range(100):
                _, baseline = agent._evemtbench_load_plan(voltage, "Load", seed)
                _, item = agent._evemtbench_load_plan(voltage, "Load", seed, "zip")
                self.assertEqual(item["powerfactory_attributes"], baseline["powerfactory_attributes"])
                self.assertEqual(item, agent._evemtbench_load_plan(voltage, "Load", seed, "zip")[1])
                for key, value in item["zip_coefficients"].items():
                    self.assertGreaterEqual(value, specs[key]["min"] - 1e-12)
                    self.assertLessEqual(value, specs[key]["max"] + 1e-12)
                for prefix in ("kP", "kQ"):
                    self.assertAlmostEqual(sum(item["zip_coefficients"][f"{prefix}_{term}"]
                                               for term in ("Z", "I", "P")), 1.0)
                self.assertNotIn("cP", item["type_attributes"])
                self.assertNotIn("cQ", item["type_attributes"])

    def test_zip_preview_and_confirm_create_dedicated_type(self):
        grid, bus, app = self.network()
        parameters = dict(load_model="zip", type_name="Research ZIP Type", out_of_service=True)
        preview = self.call(app, **parameters)
        self.assertTrue(preview["success"], preview)
        self.assertFalse(preview["applied"])
        self.assertEqual(app.equipment_folder["IntPrjfolder"], [])
        self.assertEqual(grid["ElmLod"], [])
        result = self.call(app, confirmation=preview["confirmation_required"], **parameters)
        self.assertTrue(result["success"], result)
        self.assertTrue(result["type_created"])
        typ = app.equipment_folder["IntPrjfolder"][0]["TypLod"][0]
        self.assertIs(grid["ElmLod"][0].GetAttribute("typ_id"), typ)
        self.assertEqual(grid["ElmLod"][0].GetAttribute("outserv"), 1)
        self.assertEqual(result["retained_powerfactory_attributes"]["typ_id"], typ.GetFullName())
        self.assertIn("RMS and EMT", preview["item"]["limitations"][-1])
        for key, value in preview["item"]["type_attributes"].items():
            self.assertAlmostEqual(typ.GetAttribute(key), value)
        for key, value in preview["item"]["derived_type_attributes"].items():
            self.assertAlmostEqual(typ.GetAttribute(key), value)

    def test_zip_stale_model_type_seed_or_coefficients_create_nothing(self):
        grid, bus, app = self.network()
        baseline = self.call(app)
        changed = self.call(app, load_model="zip", type_name="ZIP", confirmation=baseline["confirmation_required"])
        self.assertFalse(changed["success"])
        preview = self.call(app, load_model="zip", type_name="ZIP")
        for changes in ({"type_name": "Other ZIP"}, {"seed": 43}, {"load_model": "constant_power", "type_name": ""}):
            options = dict(load_model="zip", type_name="ZIP")
            options.update(changes)
            result = self.call(app, confirmation=preview["confirmation_required"], **options)
            self.assertFalse(result["success"], result)
        agent = agent_module.DIgSILENTAgent
        original = agent._evemtbench_load_plan
        def changed_plan(*args, **kwargs):
            kind, item = original(*args, **kwargs)
            item = copy.deepcopy(item)
            item["type_attributes"]["aP"] += 0.01
            return kind, item
        with patch.object(agent, "_evemtbench_load_plan", side_effect=changed_plan):
            result = self.call(app, load_model="zip", type_name="ZIP", confirmation=preview["confirmation_required"])
        self.assertFalse(result["success"])
        self.assertEqual(app.equipment_folder["IntPrjfolder"], [])
        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(bus["StaCubic"], [])

    def test_zip_rejects_bad_inputs_and_existing_types(self):
        grid, bus, app = self.network()
        for changes in ({"load_model": "other"}, {"load_model": "zip"},
                        {"load_model": "zip", "type_name": "x" * 41},
                        {"type_name": "unused"}, {"load_model": None}):
            result = self.call(app, **changes)
            self.assertFalse(result["success"], result)
        folder = app.equipment_folder.CreateObject("IntPrjfolder", "Load Types")
        typ = folder.CreateObject("TypLod", "Existing")
        result = self.call(app, load_model="zip", type_name="existing")
        self.assertFalse(result["success"])
        self.assertIn("already exists", result["message"])
        self.assertEqual(folder["TypLod"], [typ])

    def test_zip_failure_removes_only_new_type_and_connections(self):
        for rejected in ("aP", "plini", "typ_id"):
            grid, bus, app = self.network()
            folder = app.equipment_folder.CreateObject("IntPrjfolder", "Load Types")
            existing = folder.CreateObject("TypLod", "Keep This Type")
            if rejected == "aP":
                app.equipment_folder.reject_attribute = rejected
            else:
                grid.reject_attribute = rejected
            preview = self.call(app, load_model="zip", type_name="ZIP")
            result = self.call(app, load_model="zip", type_name="ZIP", confirmation=preview["confirmation_required"])
            self.assertFalse(result["success"], result)
            self.assertTrue(result["rolled_back"], result)
            self.assertEqual(folder["TypLod"], [existing])
            self.assertEqual(grid["ElmLod"], [])
            self.assertEqual(bus["StaCubic"], [])

    def test_zip_derived_readback_failure_rolls_back_new_folder(self):
        grid, bus, app = self.network()
        preview = self.call(app, load_model="zip", type_name="ZIP")
        original = FakeObject.GetAttribute
        def wrong_derived(obj, key):
            if obj.class_name == "TypLod" and key == "cP":
                return 999.0
            return original(obj, key)
        with patch.object(FakeObject, "GetAttribute", wrong_derived):
            result = self.call(app, load_model="zip", type_name="ZIP", confirmation=preview["confirmation_required"])
        self.assertFalse(result["success"])
        self.assertTrue(result["rolled_back"])
        self.assertEqual(app.equipment_folder["IntPrjfolder"], [])

    def test_zip_infeasible_source_ranges_fail_before_connection(self):
        agent = agent_module.DIgSILENTAgent
        database = copy.deepcopy(agent._load_evemtbench_load_database())
        for term in ("Z", "I", "P"):
            database["catalog_only"]["load_model_coefficients"][f"kP_{term}"] = {"min": 2, "max": 3}
        with patch.object(agent, "_load_evemtbench_load_database", return_value=database), \
                patch.object(agent, "_get_application") as connect:
            result = agent.create_evemtbench_component("load", dict(
                voltage_kv=20, load_name="Load", bus_name="Bus", load_model="zip", type_name="ZIP"))
        self.assertFalse(result["success"])
        self.assertIn("no feasible solution", result["message"])
        connect.assert_not_called()

    def test_unified_listing_discovers_optional_zip_inputs(self):
        metadata = agent_module.DIgSILENTAgent.list_evemtbench_components("load")["creation_parameters"]
        self.assertEqual(metadata["load_model"]["default"], "constant_power")
        self.assertEqual(metadata["type_name"]["default"], "")

    def test_default_creation_does_not_create_or_assign_a_type(self):
        grid, bus, app = self.network()
        preview = self.call(app)
        result = self.call(app, confirmation=preview["confirmation_required"])
        self.assertTrue(result["success"])
        self.assertFalse(result["type_created"])
        self.assertIsNone(grid["ElmLod"][0].GetAttribute("typ_id"))
        self.assertEqual(app.equipment_folder["IntPrjfolder"], [])

    def test_zip_confirmation_binds_type_destination_folder(self):
        grid, bus, app = self.network()
        preview = self.call(app, load_model="zip", type_name="ZIP")
        folder = app.equipment_folder.CreateObject("IntPrjfolder", "Load Types")
        result = self.call(app, load_model="zip", type_name="ZIP", confirmation=preview["confirmation_required"])
        self.assertFalse(result["success"])
        self.assertIn("confirmation must exactly match", result["message"])
        self.assertEqual(folder["TypLod"], [])

    def test_zip_reports_failed_type_or_element_cleanup(self):
        for failed_class in ("TypLod", "ElmLod"):
            with self.subTest(failed_class=failed_class):
                grid, bus, app = self.network()
                grid.reject_attribute = "plini"
                preview = self.call(app, load_model="zip", type_name="ZIP")
                create = FakeObject.CreateObject
                def failing_delete(parent, class_name, name):
                    obj = create(parent, class_name, name)
                    if class_name == failed_class:
                        obj.delete_fails = True
                    return obj
                with patch.object(FakeObject, "CreateObject", failing_delete):
                    result = self.call(app, load_model="zip", type_name="ZIP", confirmation=preview["confirmation_required"])
                self.assertFalse(result["success"])
                self.assertFalse(result["rolled_back"])
                self.assertTrue(result["type_created"])
                self.assertEqual(result["remaining_type"], "ZIP")
                self.assertEqual(len(app.equipment_folder["IntPrjfolder"][0]["TypLod"]), 1)
                if failed_class == "ElmLod":
                    self.assertIn("remaining_load", result)

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
        preview = self.call(app, voltage_kv=110.0, out_of_service=True)

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
