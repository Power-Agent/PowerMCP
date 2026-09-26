import builtins
import json
import sys
import unittest
from types import ModuleType
from unittest.mock import Mock, patch


class FakeFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self):
        return lambda function: function


class FakeAgent:
    _shared_app = None

    @classmethod
    def _get_application(cls, open_digsilent=True):
        if cls._shared_app is None:
            raise RuntimeError("PowerFactory is unavailable")
        return cls._shared_app


mcp_module = None
module_patch = None


def setUpModule():
    global mcp_module, module_patch

    mcpserver = ModuleType("mcp.server.mcpserver")
    mcpserver.MCPServer = FakeFastMCP

    agent_module = ModuleType("Agent_DIgSILENT")
    agent_module.SimulationConfig = object
    agent_module.DIgSILENTAgent = FakeAgent

    module_patch = patch.dict(
        sys.modules,
        {
            "Agent_DIgSILENT": agent_module,
            "mcp.server.mcpserver": mcpserver,
        },
    )
    module_patch.start()

    original_print = builtins.print
    try:
        import MCP_PowerFactory as module
    finally:
        builtins.print = original_print

    module._pf = lambda function, *args, **kwargs: function(
        *args,
        **kwargs,
    )
    mcp_module = module


def tearDownModule():
    sys.modules.pop("MCP_PowerFactory", None)
    module_patch.stop()


class FakeObject:
    def __init__(self, name, class_name, full_name, attributes=None, parent=None):
        self.class_name = class_name
        self.full_name = full_name
        self.parent = parent
        self.attributes = {"loc_name": name}
        self.attributes.update(attributes or {})
        self.attribute_reads = []

    def GetAttribute(self, attribute):
        self.attribute_reads.append(attribute)
        return self.attributes[attribute]

    def GetClassName(self):
        return self.class_name

    def GetFullName(self):
        return self.full_name

    def GetParent(self):
        return self.parent


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
        self.object_queries = []

    def GetActiveProject(self):
        return self.project

    def GetActiveStudyCase(self):
        return self.active_case

    def GetCalcRelevantObjects(self, query):
        self.object_queries.append(query)
        return self.objects.get(query, [])

    def GetProjectFolder(self, folder_name):
        return self.study_folder if folder_name == "study" else None


class StateInspectionTest(unittest.TestCase):
    def test_contingency_listing_and_bounded_results(self):
        fault_cases_folder = FakeObject(
            "Fault Cases",
            "IntFltcases",
            r"\user\test.IntPrj\Fault Cases.IntFltcases",
        )
        target = FakeObject(
            "Line 01 - 02",
            "ElmLne",
            r"\user\test.IntPrj\Grid\Line 01 - 02.ElmLne",
        )
        outage = FakeObject(
            "Outage Event",
            "EvtOutage",
            r"\user\test.IntPrj\Fault Cases\N-1.IntEvt\Outage Event.EvtOutage",
            {
                "p_target": target,
                "time": 0.0,
                "i_what": 0,
                "outserv": 0,
            },
        )
        switch = FakeObject(
            "Switch Event",
            "EvtSwitch",
            r"\user\test.IntPrj\Fault Cases\N-1.IntEvt\Switch Event.EvtSwitch",
            {
                "p_target": target,
                "time": 0.0,
                "i_switch": 0,
                "outserv": 0,
            },
        )
        fault_case = FakeObject(
            "N-1",
            "IntEvt",
            r"\user\test.IntPrj\Fault Cases\N-1.IntEvt",
            parent=fault_cases_folder,
        )
        fault_case.GetContents = lambda pattern, recursive: (
            [outage] if pattern == "*.EvtOutage" else
            [switch] if pattern == "*.EvtSwitch" else []
        )
        empty_fault_case = FakeObject(
            "Empty",
            "IntEvt",
            r"\user\test.IntPrj\Fault Cases\Empty.IntEvt",
            parent=fault_cases_folder,
        )
        empty_fault_case.GetContents = lambda pattern, recursive: []
        simulation_events = FakeObject(
            "Simulation Events/Fault",
            "IntEvt",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase\Simulation Events/Fault.IntEvt",
            parent=FakeObject(
                "Case 1",
                "IntCase",
                r"\user\test.IntPrj\Study Cases\Case 1.IntCase",
            ),
        )
        simulation_events.GetContents = lambda pattern, recursive: []

        project = FakeObject("test", "IntPrj", r"\user\test.IntPrj")
        project.GetContents = lambda pattern, recursive: [
            empty_fault_case,
            simulation_events,
            fault_case,
        ]
        study_case = FakeObject(
            "Case 1",
            "IntCase",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase",
        )

        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase\Contingency Analysis AC.ElmRes",
        )
        released = []
        result_file.Load = lambda: None
        result_file.Release = lambda: released.append(True)
        result_file.GetNumberOfRows = lambda: 2
        result_file.GetNumberOfColumns = lambda: 3
        result_file.GetVariable = lambda column: (
            "b:i_obj" if column == 0 else f"variable:{column}"
        )
        result_file.GetValue = lambda row, column: (
            (3, 1e35) if (row, column) == (0, 1)
            else (0, row * 10 + column)
        )
        monitored_object = FakeObject(
            "Line 01 - 02",
            "ElmLne",
            r"\user\test.IntPrj\Grid\Line 01 - 02.ElmLne",
        )
        result_file.GetObject = lambda column: (
            monitored_object if column == 1 else None
        )
        result_object = FakeObject(
            "MCP N-1 Line Test",
            "IntEvt",
            r"\user\test.IntPrj\Fault Cases\MCP N-1 Line Test.IntEvt",
        )
        result_file.GetObj = lambda index: (0, result_object)

        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase\Contingency Analysis.ComSimoutage",
            {
                "p_rescnt": result_file,
                "dat_src": "MAN",
                "iopt_method": 1,
                "iopt_Linear": 0,
                "copt_Linear": 0,
                "iACDCCombine": 0,
                "dynamicCase": 0,
            },
        )
        app = Mock()
        app.GetActiveProject.return_value = project
        app.GetActiveStudyCase.return_value = study_case
        app.GetFromStudyCase.return_value = command
        FakeAgent._shared_app = app

        configuration = json.loads(
            mcp_module.get_contingency_configuration()
        )
        self.assertTrue(configuration["success"])
        self.assertEqual(configuration["settings"], {
            "data_source": "MAN",
            "calculation_method": 1,
            "linear_method": 0,
            "linear_option": 0,
            "combine_ac_dc": 0,
            "dynamic_contingencies": 0,
        })

        contingencies = json.loads(mcp_module.list_contingencies())
        self.assertTrue(contingencies["success"])
        self.assertEqual(contingencies["total_count"], 2)
        self.assertEqual(
            contingencies["results"][0]["outages"][0]["target"]["name"],
            "Line 01 - 02",
        )
        self.assertNotIn(
            "full_name",
            contingencies["results"][0]["outages"][0],
        )
        self.assertEqual(
            contingencies["results"][1]["outage_count"],
            0,
        )
        self.assertEqual(contingencies["results"][1]["outages"], [])
        self.assertEqual(contingencies["results"][0]["event_count"], 2)
        self.assertEqual(contingencies["results"][0]["switch_count"], 1)
        self.assertEqual(
            contingencies["results"][0]["switches"][0]["target"]["name"],
            "Line 01 - 02",
        )

        limited = json.loads(mcp_module.list_contingencies(max_results=1))
        self.assertEqual(limited["results"][0]["name"], "N-1")

        results = json.loads(mcp_module.get_contingency_results(
            "ac",
            max_rows=1,
            max_columns=2,
        ))
        self.assertTrue(results["success"])
        self.assertEqual(results["total_rows"], 2)
        self.assertEqual(results["total_columns"], 3)
        self.assertEqual(results["rows"], [{
            "index": 0,
            "values": [0, None],
            "object_index": 0,
            "object": {
                "name": "MCP N-1 Line Test",
                "class_name": "IntEvt",
                "full_name": r"\user\test.IntPrj\Fault Cases\MCP N-1 Line Test.IntEvt",
            },
            "errors": [{"column": 1, "code": 3}],
        }])
        self.assertNotIn("element", results["columns"][0])
        self.assertEqual(results["columns"][1]["object"], {
            "name": "Line 01 - 02",
            "class_name": "ElmLne",
            "full_name": r"\user\test.IntPrj\Grid\Line 01 - 02.ElmLne",
        })
        self.assertTrue(results["truncated"])
        self.assertEqual(released, [True])

        oversized = json.loads(mcp_module.get_contingency_results(
            "ac",
            max_rows=1000,
            max_columns=1000,
        ))
        self.assertFalse(oversized["success"])

    def test_add_contingency_result_variables_updates_elmres_selection(self):
        bus = FakeObject(
            "Bus 08",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 08.ElmTerm",
        )
        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes",
        )
        result_file.AddVariable = Mock(return_value=0)
        result_file.Load = Mock(return_value=0)
        result_file.Release = Mock()
        result_file.FindColumn = Mock(
            side_effect=lambda obj, variable: 13 if variable == "m:u" else -1
        )
        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Case 1\Contingency Analysis.ComSimoutage",
            {"p_rescnt": result_file},
        )
        command.Execute = Mock()
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        app.GetCalcRelevantObjects.return_value = [bus]
        FakeAgent._shared_app = app

        result = json.loads(mcp_module.add_contingency_result_variables(
            "Bus 08.ElmTerm",
            ["m:u", "m:phiu", "m:u"],
        ))

        self.assertTrue(result["success"])
        self.assertEqual(result["configured_objects"], 1)
        self.assertEqual(result["configured_variables"], 2)
        self.assertEqual(result["variables"], ["m:u", "m:phiu"])
        result_file.AddVariable.assert_any_call(bus, "m:phiu")
        self.assertEqual(result_file.AddVariable.call_count, 1)
        result_file.Load.assert_called_once_with()
        result_file.Release.assert_called_once_with()
        command.Execute.assert_not_called()

    def _result_recording_app(self, objects, recorded):
        """Fake an AC result file whose registered columns are ``recorded``."""
        columns = set(recorded)
        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes",
        )
        result_file.Load = Mock(return_value=0)
        result_file.Release = Mock()
        result_file.FindColumn = Mock(side_effect=lambda obj, variable: (
            7 if (obj.GetAttribute("loc_name"), variable) in columns else -1
        ))

        def add_variable(obj, variable):
            columns.add((obj.GetAttribute("loc_name"), variable))
            return 0

        result_file.AddVariable = Mock(side_effect=add_variable)
        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Case 1\Contingency Analysis.ComSimoutage",
            {"p_rescnt": result_file},
        )
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        app.GetCalcRelevantObjects.return_value = objects
        FakeAgent._shared_app = app
        return result_file, columns

    def test_add_contingency_result_variables_reports_whether_anything_changed(self):
        # A repeat must be distinguishable from a first call, and must not send
        # the caller off to rerun the analysis when nothing was added.
        bus = FakeObject("Bus 08", "ElmTerm", r"\user\test.IntPrj\Grid\Bus 08.ElmTerm")
        result_file, _ = self._result_recording_app([bus], set())

        first = json.loads(mcp_module.add_contingency_result_variables(
            "Bus 08.ElmTerm", ["m:u", "m:phiu"],
        ))
        self.assertTrue(first["success"])
        self.assertEqual(first["added_variables"], 2)
        self.assertEqual(first["already_recorded_variables"], 0)
        self.assertEqual(first["results"][0]["added"], ["m:u", "m:phiu"])
        self.assertIn("rerun contingency analysis", first["message"])

        repeat = json.loads(mcp_module.add_contingency_result_variables(
            "Bus 08.ElmTerm", ["m:u", "m:phiu"],
        ))
        self.assertTrue(repeat["success"])
        self.assertEqual(repeat["added_variables"], 0)
        self.assertEqual(repeat["already_recorded_variables"], 2)
        self.assertEqual(repeat["results"][0]["added"], [])
        self.assertEqual(
            repeat["results"][0]["already_recorded"], ["m:u", "m:phiu"],
        )
        self.assertNotIn("rerun", repeat["message"])
        self.assertEqual(result_file.AddVariable.call_count, 2)

    def test_add_contingency_result_variables_keeps_record_after_an_object_fails(self):
        # An object that cannot be described must not take the whole call down
        # as a failed "read" and erase the record of columns already added.
        class Detached(FakeObject):
            def GetFullName(self):
                raise RuntimeError("COM object detached")

        good = FakeObject("Bus 1", "ElmTerm", r"\user\test.IntPrj\Grid\Bus 1.ElmTerm")
        bad = Detached("Bus 3", "ElmTerm", r"\user\test.IntPrj\Grid\Bus 3.ElmTerm")
        _, columns = self._result_recording_app([good, bad], set())

        result = json.loads(mcp_module.add_contingency_result_variables(
            "*.ElmTerm", ["m:u"],
        ))

        self.assertFalse(result["success"])
        self.assertNotIn("read failed", result["message"])
        self.assertEqual(result["added_variables"], 1)
        self.assertEqual(result["results"][0]["object"]["name"], "Bus 1")
        self.assertEqual(result["results"][0]["added"], ["m:u"])
        self.assertIn("COM object detached", result["errors"][0]["message"])
        self.assertEqual(result["errors"][0]["object_index"], 1)
        # An object that cannot be identified is not written to.
        self.assertEqual(columns, {("Bus 1", "m:u")})

    def test_contingency_summary_reports_violations(self):
        bus = FakeObject(
            "Bus 08",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 08.ElmTerm",
        )
        line = FakeObject(
            "Line 06 - 07",
            "ElmLne",
            r"\user\test.IntPrj\Grid\Line 06 - 07.ElmLne",
        )
        outage_line = FakeObject(
            "Line 01 - 02",
            "ElmLne",
            r"\user\test.IntPrj\Grid\Line 01 - 02.ElmLne",
        )
        outage_bus = FakeObject(
            "Bus 08",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 08.ElmTerm",
        )
        contingency = FakeObject(
            "MCP N-1 Line Test",
            "ComOutage",
            r"\user\test.IntPrj\Case 1\MCP N-1 Line Test.ComOutage",
        )
        affected = [outage_line, outage_bus]
        contingency.GetObject = lambda index: (
            affected[index] if index < len(affected) else None
        )

        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes",
        )
        released = []
        result_file.Load = lambda: None
        result_file.Release = lambda: released.append(True)
        result_file.GetNumberOfRows = lambda: 2
        result_file.GetNumberOfColumns = lambda: 4
        result_file.GetVariable = lambda column: (
            "b:i_obj", "b:inoconv", "m:u", "c:loading"
        )[column]
        result_file.GetObject = lambda column: (
            bus if column == 2 else line if column == 3 else None
        )
        values = (
            (0.0, 0.0, 1.0, 50.0),
            (-1.0, 0.0, 0.89, 120.0),
        )
        result_file.GetValue = lambda row, column: (0, values[row][column])
        result_file.GetObj = lambda index: contingency if index == -1 else None

        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Case 1\Contingency Analysis.ComSimoutage",
            {"p_rescnt": result_file},
        )
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        FakeAgent._shared_app = app

        summary = json.loads(mcp_module.get_contingency_summary(
            max_affected_elements=1,
        ))

        self.assertTrue(summary["success"])
        self.assertEqual(summary["total_count"], 1)
        self.assertEqual(
            summary["results"][0]["affected_elements"][0]["name"],
            "Line 01 - 02",
        )
        self.assertEqual(
            summary["results"][0]["total_affected_elements"],
            2,
        )
        self.assertEqual(
            summary["results"][0]["returned_affected_elements"],
            1,
        )
        self.assertTrue(
            summary["results"][0]["affected_elements_truncated"]
        )
        self.assertEqual(
            summary["results"][0]["voltage_violations"][0]["voltage_pu"],
            0.89,
        )
        self.assertEqual(
            summary["results"][0]["overloads"][0]["loading_pct"],
            120.0,
        )
        self.assertTrue(summary["results"][0]["converged"])
        self.assertEqual(summary["base_case"]["maximum_loading"]["loading_pct"], 50.0)
        self.assertEqual(released, [True])

        # A GetObject that never returns None must stop at the cap. The probe
        # list also stops the test itself: an unbounded walk fails here fast
        # instead of hanging CI, which sets no pytest timeout.
        probes = []

        def never_none(index):
            probes.append(index)
            if len(probes) > 10:
                raise AssertionError("affected element scan did not stop")
            return outage_line

        contingency.GetObject = never_none
        with patch.object(mcp_module, "_MAX_AFFECTED_ELEMENT_SCAN", 2):
            unbounded = json.loads(mcp_module.get_contingency_summary())
        self.assertFalse(unbounded["success"])
        self.assertIn("scan exceeded the safe limit", unbounded["message"])
        self.assertEqual(probes, [0, 1, 2])
        self.assertEqual(released, [True, True])

        # Exactly as many elements as the cap is a complete scan, not an
        # overflow: the walk has to probe one index past the last element to
        # see PowerFactory's terminating None.
        contingency.GetObject = lambda index: (
            affected[index] if index < len(affected) else None
        )
        with patch.object(
            mcp_module, "_MAX_AFFECTED_ELEMENT_SCAN", len(affected)
        ):
            at_cap = json.loads(mcp_module.get_contingency_summary())
        self.assertTrue(at_cap["success"], at_cap.get("message"))
        self.assertEqual(
            at_cap["results"][0]["total_affected_elements"],
            len(affected),
        )

        # max_affected_elements clamps to 1000, so the scan cap must sit above
        # it or affected_elements_truncated could never be reported.
        self.assertGreater(mcp_module._MAX_AFFECTED_ELEMENT_SCAN, 1000)

    def test_agent_result_serializes_tuple_result(self):
        with patch.object(
            FakeAgent,
            "short_circuit",
            return_value=(True, "Short-circuit calculation OK"),
            create=True,
        ):
            result = json.loads(
                mcp_module._agent_result("short_circuit", False)
            )

        self.assertEqual(result, {
            "success": True,
            "message": "Short-circuit calculation OK",
        })

    def test_get_parameters_serializes_object_lists(self):
        reference = FakeObject(
            "Bus 02",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 02.ElmTerm",
        )
        bus = FakeObject(
            "Bus 01",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 01.ElmTerm",
            {"references": [reference]},
        )
        FakeAgent._shared_app = FakeApplication(
            project=None,
            active_case=None,
            study_cases=[],
            objects={"*.ElmTerm": [bus]},
        )

        result = json.loads(mcp_module.get_parameters(
            "*.ElmTerm",
            ["references"],
        ))

        self.assertTrue(result["success"])
        self.assertEqual(
            result["results"][0]["values"]["references"],
            [str(reference)],
        )

    def test_read_only_tools_connect_on_cold_start(self):
        project = FakeObject("test", "IntPrj", r"\user\test.IntPrj")
        case = FakeObject(
            "Case 1",
            "IntCase",
            r"\user\test.IntPrj\Study Cases\Case 1.IntCase",
        )
        bus = FakeObject(
            "Bus 01",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 01.ElmTerm",
            {"uknom": 345.0, "outserv": 0},
        )
        app = FakeApplication(
            project=project,
            active_case=case,
            study_cases=[case],
            objects={"*.ElmTerm": [bus]},
        )
        FakeAgent._shared_app = None

        with patch.object(
            FakeAgent,
            "_get_application",
            return_value=app,
        ) as get_application:
            results = [
                json.loads(mcp_module.get_active_project()),
                json.loads(mcp_module.get_active_study_case()),
                json.loads(mcp_module.get_parameters(
                    "*.ElmTerm",
                    ["uknom"],
                )),
                json.loads(mcp_module.list_objects("*.ElmTerm")),
                json.loads(mcp_module.list_components("buses")),
                json.loads(mcp_module.list_study_cases()),
            ]

        self.assertTrue(all(result["success"] for result in results))
        self.assertEqual(get_application.call_count, 6)
        for call in get_application.call_args_list:
            self.assertFalse(call.kwargs["open_digsilent"])

        with patch.object(
            FakeAgent,
            "_get_application",
            side_effect=RuntimeError("PowerFactory is unavailable"),
        ):
            failure = json.loads(mcp_module.get_active_project())

        self.assertFalse(failure["success"])
        self.assertIn("PowerFactory is unavailable", failure["message"])

        with (
            patch.object(FakeAgent, "_get_application", return_value=app),
            patch.object(
                app,
                "GetActiveProject",
                side_effect=RuntimeError("project lookup failed"),
            ),
        ):
            failure = json.loads(mcp_module.get_active_project())

        self.assertFalse(failure["success"])
        self.assertIn("project lookup failed", failure["message"])

    def test_delete_component_preserves_partial_deletion_result(self):
        expected = {
            "success": False,
            "deleted": True,
            "graphics": {
                "requested": True,
                "matched": 1,
                "deleted": 0,
                "remaining": [r"\user\Grid\Load Symbol.IntGrf"],
                "refresh": "rebuilt",
            },
            "message": "Component deleted, but graphical objects remain",
        }

        with (
            patch.object(FakeAgent, "delete_component", create=True),
            patch.object(mcp_module, "_pf", return_value=expected),
        ):
            result = json.loads(mcp_module.delete_component(
                "load",
                "Load 1",
                confirmation="DELETE load Load 1",
                update_graphics=True,
            ))

        self.assertEqual(result, expected)

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
            unsupported = FakeObject(
                "Shunt 1",
                "ElmShnt",
                r"\user\test.IntPrj\Grid\Shunt 1.ElmShnt",
                {"outserv": 0},
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
                    "*.Elm*": [bus, line, transformer, unsupported],
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

            transformer.attribute_reads.clear()
            limited = json.loads(
                mcp_module.list_components("branches", max_results=1)
            )
            self.assertEqual(limited["total_count"], 2)
            self.assertEqual(limited["returned_count"], 1)
            self.assertNotIn("outserv", transformer.attribute_reads)
            self.assertNotIn("loc_name", transformer.attribute_reads)

            all_components = json.loads(
                mcp_module.list_components("all", max_results=10)
            )
            self.assertEqual(all_components["total_count"], 3)
            self.assertEqual(all_components["queries"], ["*.Elm*"])
            self.assertEqual(
                FakeAgent._shared_app.object_queries[-1:],
                ["*.Elm*"],
            )

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
