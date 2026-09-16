import builtins
import json
import sys
import unittest
from types import ModuleType


fastmcp = ModuleType("fastmcp")


class FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self):
        return lambda function: function


fastmcp.FastMCP = FakeFastMCP
sys.modules["fastmcp"] = fastmcp


class FakeAgent:
    _shared_app = None


agent_module = ModuleType("Agent_DIgSILENT")
agent_module.SimulationConfig = object
agent_module.DIgSILENTAgent = FakeAgent
sys.modules["Agent_DIgSILENT"] = agent_module

original_print = builtins.print
import MCP_PowerFactory as mcp_module
builtins.print = original_print

mcp_module._pf = lambda function, *args, **kwargs: function(*args, **kwargs)


class FakeObject:
    def __init__(self, name, class_name, full_name, attributes=None):
        self.class_name = class_name
        self.full_name = full_name
        self.attributes = {"loc_name": name}
        self.attributes.update(attributes or {})

    def GetAttribute(self, attribute):
        return self.attributes[attribute]

    def GetClassName(self):
        return self.class_name

    def GetFullName(self):
        return self.full_name


class FakeFolder:
    def __init__(self, contents):
        self.contents = contents

    def GetContents(self, pattern, recursive):
        return self.contents


class FakeApplication:
    def __init__(self, project, active_case, study_cases, objects):
        self.project = project
        self.active_case = active_case
        self.study_folder = FakeFolder(study_cases)
        self.objects = objects

    def GetActiveProject(self):
        return self.project

    def GetActiveStudyCase(self):
        return self.active_case

    def GetCalcRelevantObjects(self, query):
        return self.objects.get(query, [])

    def GetProjectFolder(self, folder_name):
        return self.study_folder if folder_name == "study" else None


class StateInspectionTest(unittest.TestCase):
    def test_state_and_discovery_tools(self):
        project = FakeObject(
            "test",
            "IntPrj",
            r"\user\test.IntPrj",
        )
        case_1 = FakeObject(
            "Case 1",
            "IntCase",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase",
        )
        case_2 = FakeObject(
            "Case 2",
            "IntCase",
            r"\user\test.IntPrj\Study Cases\Case 2.IntCase",
        )
        bus_1 = FakeObject(
            "Bus 01",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 01.ElmTerm",
            {"m:u": 1.047, "uknom": 345.0},
        )
        bus_2 = FakeObject(
            "Bus 02",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 02.ElmTerm",
            {"m:u": 1.049, "uknom": 345.0},
        )

        FakeAgent._shared_app = FakeApplication(
            project=project,
            active_case=case_1,
            study_cases=[case_1, case_2],
            objects={"*.ElmTerm": [bus_1, bus_2]},
        )

        active_project = json.loads(mcp_module.get_active_project())
        self.assertTrue(active_project["success"])
        self.assertEqual(active_project["name"], "test")

        active_case = json.loads(mcp_module.get_active_study_case())
        self.assertTrue(active_case["success"])
        self.assertEqual(active_case["name"], "Case 1")

        parameters = json.loads(
            mcp_module.get_parameters(
                "*.ElmTerm",
                ["m:u", "uknom", "m:u"],
                max_results=1,
            )
        )
        self.assertTrue(parameters["success"])
        self.assertEqual(parameters["variables"], ["m:u", "uknom"])
        self.assertEqual(parameters["total_count"], 2)
        self.assertEqual(parameters["returned_count"], 1)
        self.assertEqual(parameters["results"][0]["name"], "Bus 01")
        self.assertEqual(
            parameters["results"][0]["values"],
            {"m:u": 1.047, "uknom": 345.0},
        )

        objects = json.loads(
            mcp_module.list_objects("*.ElmTerm", max_results=1)
        )
        self.assertEqual(objects["total_count"], 2)
        self.assertEqual(objects["returned_count"], 1)
        self.assertEqual(objects["results"][0]["name"], "Bus 01")

        cases = json.loads(mcp_module.list_study_cases(max_results=10))
        self.assertEqual(cases["total_count"], 2)
        self.assertTrue(cases["results"][0]["is_active"])
        self.assertFalse(cases["results"][1]["is_active"])

        FakeAgent._shared_app = None
        disconnected = json.loads(mcp_module.get_active_project())
        self.assertFalse(disconnected["success"])

    def test_list_components(self):
            bus = FakeObject(
                "Bus 01",
                "ElmTerm",
                r"\user\test.IntPrj\Grid\Bus 01.ElmTerm",
                {"outserv": 0},
            )
            line = FakeObject(
                "Line 01 - 02",
                "ElmLne",
                r"\user\test.IntPrj\Grid\Line 01 - 02.ElmLne",
                {"outserv": 0},
            )
            transformer = FakeObject(
                "Trf 02 - 30",
                "ElmTr2",
                r"\user\test.IntPrj\Grid\Trf 02 - 30.ElmTr2",
                {"outserv": 1},
            )

            FakeAgent._shared_app = FakeApplication(
                project=None,
                active_case=None,
                study_cases=[],
                objects={
                    "*.ElmTerm": [bus],
                    "*.ElmLne": [line],
                    "*.ElmTr2": [transformer],
                    "*.ElmTr3": [],
                    "*.ElmCoup": [],
                },
            )

            buses = json.loads(
                mcp_module.list_components("buses", max_results=10)
            )
            self.assertTrue(buses["success"])
            self.assertEqual(buses["total_count"], 1)
            self.assertEqual(buses["results"][0]["name"], "Bus 01")

            branches = json.loads(
                mcp_module.list_components("branches", max_results=10)
            )
            self.assertTrue(branches["success"])
            self.assertEqual(branches["total_count"], 2)
            self.assertEqual(branches["returned_count"], 2)
            self.assertEqual(
                {item["class_name"] for item in branches["results"]},
                {"ElmLne", "ElmTr2"},
            )

            transformers = json.loads(
                mcp_module.list_components(
                    "transformers",
                    max_results=10,
                )
            )
            self.assertEqual(transformers["total_count"], 1)
            self.assertTrue(
                transformers["results"][0]["out_of_service"]
            )

            limited = json.loads(
                mcp_module.list_components("branches", max_results=1)
            )
            self.assertEqual(limited["total_count"], 2)
            self.assertEqual(limited["returned_count"], 1)

            unsupported = json.loads(
                mcp_module.list_components("unknown")
            )
            self.assertFalse(unsupported["success"])
            self.assertIn(
                "buses",
                unsupported["supported_component_types"],
            )


if __name__ == "__main__":
    unittest.main()
