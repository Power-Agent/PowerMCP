import unittest

import Agent_DIgSILENT as agent_module


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


if __name__ == "__main__":
    unittest.main()
