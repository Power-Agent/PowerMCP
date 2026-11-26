import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module


class UnifiedEvEMTBenchListingTest(unittest.TestCase):
    def test_lists_all_six_catalogs_without_powerfactory(self):
        agent = agent_module.DIgSILENTAgent
        with patch.object(agent, "_get_application", side_effect=AssertionError("must stay offline")):
            for kind in agent._evemtbench_creators:
                with self.subTest(component_type=kind):
                    result = agent.list_evemtbench_components(kind)
                    self.assertTrue(result["success"], result.get("message"))
                    self.assertEqual(result["component_type"], kind)
                    self.assertGreater(result["returned_count"], 0)
                    self.assertIn("source", result)
                    self.assertIn("catalog_id", result)
                    inputs = result["creation_parameters"]
                    self.assertEqual(inputs["confirmation"],
                                     {"type": "string", "required": False, "default": ""})
                    self.assertTrue(inputs["open_digsilent"]["default"])
                    self.assertFalse(any(name.startswith("_") for name in inputs))
        transformer = agent.list_evemtbench_components("transformer")
        self.assertEqual(transformer["creation_parameters"]["clock_number"],
                         {"type": "integer", "required": True})
        line = agent.list_evemtbench_components("overhead_line")
        self.assertTrue(line["available_filters"]["voltage_kv"]["nullable"])
        self.assertFalse(line["available_filters"]["voltage_kv"]["required"])

    def test_routes_filters_and_preserves_catalog_limits(self):
        agent = agent_module.DIgSILENTAgent
        cases = (
            ("transformer", {"voltage_class": "345/25", "rated_power_mva": 800}),
            ("overhead_line", {"voltage_kv": 110, "profile": "p50"}),
            ("underground_cable", {"profile": "p95"}),
            ("external_grid", {"voltage_kv": 110}),
            ("load", {"voltage_kv": 20}),
            ("synchronous_machine", {"machine_type": "salient_pole"}),
        )
        for kind, filters in cases:
            with self.subTest(component_type=kind):
                original = dict(filters)
                result = agent.list_evemtbench_components(kind, filters)
                self.assertTrue(result["success"], result.get("message"))
                self.assertEqual(result["returned_count"], 1)
                self.assertEqual(filters, original)
                self.assertEqual(result["component_type"], kind)
        transformer = agent.list_evemtbench_components(*cases[0])
        self.assertEqual(transformer["unmapped_source_tables"], [10, 12])
        self.assertEqual(transformer["results"][0]["ratings"][0]["rated_power_mva"], 800)
        line = agent.list_evemtbench_components(*cases[1])
        self.assertEqual(set(line["results"][0]["electrical_profiles"]), {"p50"})
        machine = agent.list_evemtbench_components(*cases[-1])
        self.assertIsNone(machine["results"][0]["parameters"]["xq_transient_pu"])
        self.assertIn("salient-pole creation remains disabled", machine["powerfactory"]["status"])

    def test_rejects_bad_types_filters_and_private_options(self):
        agent = agent_module.DIgSILENTAgent
        unknown = agent.list_evemtbench_components("unsupported")
        self.assertFalse(unknown["success"])
        self.assertEqual(len(unknown["supported_component_types"]), 6)
        for filters in ([], {"_database_loader": "override"}, {"voltage_class": "20"}, {"open_digsilent": True}):
            with self.subTest(filters=filters):
                result = agent.list_evemtbench_components("load", filters)
                self.assertFalse(result["success"])
                self.assertIn("available_filters", result)
        invalid = agent.list_evemtbench_components("overhead_line", {"profile": "made-up"})
        self.assertFalse(invalid["success"])
        self.assertIn("p50", invalid["message"])


class UnifiedEvEMTBenchCreatorTest(unittest.TestCase):
    class FakeAgent(agent_module.DIgSILENTAgent):
        calls = []

        @classmethod
        def _record(cls, name, **parameters):
            cls.calls.append((name, parameters))
            return {"success": True, "applied": False}

        @classmethod
        def create_evemtbench_transformer(cls, **parameters):
            return cls._record("transformer", **parameters)

        @classmethod
        def create_evemtbench_line(cls, **parameters):
            return cls._record("overhead_line", **parameters)

        @classmethod
        def create_evemtbench_cable(cls, **parameters):
            return cls._record("underground_cable", **parameters)

        @classmethod
        def create_evemtbench_external_grid(cls, **parameters):
            return cls._record("external_grid", **parameters)

        @classmethod
        def create_evemtbench_load(cls, **parameters):
            return cls._record("load", **parameters)

        @classmethod
        def create_evemtbench_synchronous_machine(cls, **parameters):
            return cls._record("synchronous_machine", **parameters)

    def setUp(self):
        self.FakeAgent.calls = []

    def test_routes_each_supported_component_without_mutating_parameters(self):
        for kind in (
            "transformer",
            "overhead_line",
            "underground_cable",
            "external_grid",
            "load",
            "synchronous_machine",
        ):
            parameters = {"confirmation": ""}
            result = self.FakeAgent.create_evemtbench_component(
                kind,
                parameters,
            )

            self.assertTrue(result["success"])
            self.assertEqual(result["component_type"], kind)
            self.assertEqual(parameters, {"confirmation": ""})

        self.assertEqual(
            [name for name, _ in self.FakeAgent.calls],
            [
                "transformer",
                "overhead_line",
                "underground_cable",
                "external_grid",
                "load",
                "synchronous_machine",
            ],
        )

    def test_rejects_unknown_types_and_private_options(self):
        unknown = self.FakeAgent.create_evemtbench_component(
            "generator",
            {},
        )
        private = self.FakeAgent.create_evemtbench_component(
            "overhead-line",
            {"_database_loader": "replacement"},
        )

        self.assertFalse(unknown["success"])
        self.assertIn("synchronous_machine", unknown["message"])
        self.assertFalse(private["success"])
        self.assertEqual(private["component_type"], "overhead_line")
        self.assertIn("private options", private["message"])

    def test_returns_parameter_errors_as_data(self):
        result = agent_module.DIgSILENTAgent.create_evemtbench_component(
            "load",
            {"voltage_kv": 20},
        )

        self.assertFalse(result["success"])
        self.assertFalse(result["applied"])
        self.assertIn("Invalid load parameters", result["message"])

    def test_rejects_non_boolean_flags_before_connecting(self):
        agent = agent_module.DIgSILENTAgent
        with patch.object(agent, "_get_application") as connect:
            for kind, method_name in agent._evemtbench_creators.items():
                inputs = agent.list_evemtbench_components(kind)["creation_parameters"]
                parameters = {name: "" for name, spec in inputs.items() if spec["required"]}
                for flag in ("out_of_service", "open_digsilent"):
                    for value in ("false", "true", 0, 1, None, [], {}):
                        for confirmation in ("", "stale confirmation"):
                            for unified in (False, True):
                                with self.subTest(kind=kind, flag=flag, value=value,
                                                  confirmation=confirmation, unified=unified):
                                    options = dict(parameters, **{flag: value},
                                                   confirmation=confirmation)
                                    original = dict(options)
                                    if unified:
                                        result = agent.create_evemtbench_component(kind, options)
                                    else:
                                        result = getattr(agent, method_name)(**options)
                                    self.assertFalse(result["success"])
                                    self.assertFalse(result["applied"])
                                    self.assertEqual(result["message"], f"{flag} must be a boolean")
                                    self.assertEqual(options, original)
            connect.assert_not_called()

    def test_routes_real_booleans_without_coercion(self):
        for kind in self.FakeAgent._evemtbench_creators:
            for value in (False, True):
                with self.subTest(kind=kind, value=value):
                    parameters = {"out_of_service": value, "open_digsilent": value}
                    result = self.FakeAgent.create_evemtbench_component(kind, parameters)
                    self.assertTrue(result["success"])
                    self.assertIs(self.FakeAgent.calls[-1][1]["out_of_service"], value)
                    self.assertIs(self.FakeAgent.calls[-1][1]["open_digsilent"], value)


if __name__ == "__main__":
    unittest.main()
