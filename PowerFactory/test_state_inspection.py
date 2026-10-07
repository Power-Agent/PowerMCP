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

    def SetAttribute(self, attribute, value):
        self.attributes[attribute] = value

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
                "screeningMeth": 0,
                "scrCritSimple": 1,
                "maxLoadAbs": 100.0,
                "scrCritComb": 1,
                "maxLoad": 80.0,
                "diffLoadBase": 5.0,
                "iIgnCriticalBC": 0,
                "screenRecOnly": 1,
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
            "screening_method": "dc",
            "simple_loading_criterion": True,
            "simple_loading_threshold_pct": 100.0,
            "combined_loading_criterion": True,
            "combined_loading_threshold_pct": 80.0,
            "relative_loading_change_pct": 5.0,
            "ignore_base_case_overloads": False,
            "screen_only_recorded_elements": True,
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
        monitor = FakeObject("Selection", "IntMon", "Selection.IntMon", {"obj_id": bus})
        monitor.NVars = Mock(return_value=1)
        monitor.GetVar = Mock(return_value="m:u")
        result_file.GetContents = Mock(return_value=[monitor])
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
        result_file.Load.assert_not_called()
        result_file.Release.assert_not_called()
        result_file.FindColumn.assert_not_called()
        command.Execute.assert_not_called()

    def _result_recording_app(self, objects, recorded):
        """Fake live IntMon selections, including distinct wrappers for targets."""
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

        monitors = []

        def ensure_monitor(obj):
            name = obj.GetAttribute("loc_name")
            for monitor in monitors:
                if monitor.GetAttribute("loc_name") == name:
                    return monitor
            target = FakeObject(name, obj.GetClassName(), obj.GetFullName())
            monitor = FakeObject(name, "IntMon", name + ".IntMon", {"obj_id": target})
            monitor.NVars = Mock(side_effect=lambda: len(selected_variables(name)))
            monitor.GetVar = Mock(side_effect=lambda index: selected_variables(name)[index])

            def remove_variable(variable):
                if (name, variable) not in columns:
                    return 1
                columns.remove((name, variable))
                return 0

            monitor.RemoveVar = Mock(side_effect=remove_variable)
            monitors.append(monitor)
            return monitor

        def selected_variables(name):
            return sorted(variable for object_name, variable in columns if object_name == name)

        for obj in objects:
            if selected_variables(obj.GetAttribute("loc_name")):
                ensure_monitor(obj)
        result_file.GetContents = Mock(return_value=monitors)

        def add_variable(obj, variable):
            ensure_monitor(obj)
            columns.add((obj.GetAttribute("loc_name"), variable))
            return 0

        result_file.AddVariable = Mock(side_effect=add_variable)
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

    def test_contingency_result_variables_reject_invalid_entries(self):
        for function in (
            mcp_module.add_contingency_result_variables,
            mcp_module.remove_contingency_result_variables,
        ):
            with self.subTest(function=function.__name__):
                result = json.loads(function(
                    "Bus 08.ElmTerm", ["m:u", 7, ""],
                ))
                self.assertFalse(result["success"])
                self.assertIn("indexes 1, 2", result["message"])

    def test_configure_contingency_screening_updates_and_rolls_back(self):
        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Case 1\Contingency Analysis.ComSimoutage",
            {
                "screeningMeth": 0,
                "scrCritSimple": 1,
                "maxLoadAbs": 100.0,
                "scrCritComb": 1,
                "maxLoad": 80.0,
                "diffLoadBase": 5.0,
                "iIgnCriticalBC": 0,
                "screenRecOnly": 1,
            },
        )
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        FakeAgent._shared_app = app

        result = json.loads(mcp_module.configure_contingency_screening(
            screening_method="ac_linearised",
            simple_loading_threshold_pct=110,
            combined_loading_threshold_pct=85,
            relative_loading_change_pct=7.5,
            ignore_base_case_overloads=True,
            screen_only_recorded_elements=False,
        ))

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result["changed"])
        self.assertEqual(result["before"]["screening_method"], "dc")
        self.assertEqual(result["settings"], {
            "screening_method": "ac_linearised",
            "simple_loading_criterion": True,
            "simple_loading_threshold_pct": 110.0,
            "combined_loading_criterion": True,
            "combined_loading_threshold_pct": 85.0,
            "relative_loading_change_pct": 7.5,
            "ignore_base_case_overloads": True,
            "screen_only_recorded_elements": False,
        })

        original = command.SetAttribute
        failed = False

        def fail_once(attribute, value):
            nonlocal failed
            if attribute == "maxLoad" and not failed:
                failed = True
                raise RuntimeError("write failed")
            original(attribute, value)

        command.SetAttribute = fail_once
        rolled_back = json.loads(mcp_module.configure_contingency_screening(
            screening_method="dc",
            combined_loading_threshold_pct=75,
        ))
        self.assertFalse(rolled_back["success"])
        self.assertIn("write failed", rolled_back["message"])
        self.assertEqual(command.GetAttribute("screeningMeth"), 1)
        self.assertEqual(command.GetAttribute("maxLoad"), 85.0)

        invalid = json.loads(mcp_module.configure_contingency_screening(
            relative_loading_change_pct=-1,
        ))
        self.assertFalse(invalid["success"])
        self.assertIn("finite and non-negative", invalid["message"])

    def test_add_contingency_result_variable_ignores_stale_result_column(self):
        bus = FakeObject(
            "Bus 08",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 08.ElmTerm",
        )
        selected = ["m:u"]
        monitor = FakeObject(
            "Bus 08 Results",
            "IntMon",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes\Bus 08 Results.IntMon",
            {"obj_id": bus},
        )
        monitor.NVars = lambda: len(selected)
        monitor.GetVar = lambda index: selected[index]
        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes",
        )
        result_file.GetContents = Mock(return_value=[monitor])
        result_file.FindColumn = Mock(return_value=13)
        result_file.Load = Mock(return_value=0)
        result_file.Release = Mock()
        result_file.AddVariable = Mock(
            side_effect=lambda _obj, variable: selected.append(variable) or 0
        )
        command = FakeObject(
            "Contingency Analysis",
            "ComSimoutage",
            r"\user\test.IntPrj\Case 1\Contingency Analysis.ComSimoutage",
            {"p_rescnt": result_file},
        )
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        app.GetCalcRelevantObjects.return_value = [bus]
        FakeAgent._shared_app = app

        result = json.loads(mcp_module.add_contingency_result_variables(
            "Bus 08.ElmTerm", ["m:phiu"],
        ))

        self.assertTrue(result["success"])
        self.assertEqual(result["added_variables"], 1)
        self.assertEqual(selected, ["m:u", "m:phiu"])
        result_file.AddVariable.assert_called_once_with(bus, "m:phiu")
        result_file.FindColumn.assert_not_called()
        result_file.Load.assert_not_called()

    def test_remove_contingency_result_variables_updates_intmon_selection(self):
        bus = FakeObject(
            "Bus 08",
            "ElmTerm",
            r"\user\test.IntPrj\Grid\Bus 08.ElmTerm",
        )
        selected = {"m:u"}
        monitor = FakeObject(
            "Bus 08 Results",
            "IntMon",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes\Bus 08 Results.IntMon",
            {"obj_id": bus},
        )

        def remove_variable(variable):
            if variable not in selected:
                return 1
            selected.remove(variable)
            return 0

        monitor.RemoveVar = Mock(side_effect=remove_variable)
        monitor.NVars = Mock(side_effect=lambda: len(selected))
        monitor.GetVar = Mock(side_effect=lambda index: sorted(selected)[index])
        result_file = FakeObject(
            "Contingency Analysis AC",
            "ElmRes",
            r"\user\test.IntPrj\Case 1\Contingency Analysis AC.ElmRes",
        )
        result_file.GetContents = Mock(return_value=[monitor])
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

        first = json.loads(mcp_module.remove_contingency_result_variables(
            "Bus 08.ElmTerm", ["m:u", "m:phiu", "m:u"],
        ))
        self.assertTrue(first["success"])
        self.assertEqual(first["variables"], ["m:u", "m:phiu"])
        self.assertEqual(first["removed_variables"], 1)
        self.assertEqual(first["already_absent_variables"], 1)
        self.assertEqual(first["results"][0]["removed"], ["m:u"])
        self.assertIn("rerun contingency analysis", first["message"])

        repeat = json.loads(mcp_module.remove_contingency_result_variables(
            "Bus 08.ElmTerm", ["m:u", "m:phiu"],
        ))
        self.assertTrue(repeat["success"])
        self.assertEqual(repeat["removed_variables"], 0)
        self.assertEqual(repeat["already_absent_variables"], 2)
        self.assertNotIn("rerun", repeat["message"])
        self.assertEqual(selected, set())
        command.Execute.assert_not_called()

    def test_remove_failures_are_not_reported_as_absent(self):
        bus = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        for outcome in (RuntimeError("remove failed"), 2):
            with self.subTest(outcome=outcome):
                result_file, columns = self._result_recording_app([bus], {("Bus 1", "m:u")})
                monitor = result_file.GetContents.return_value[0]
                monitor.RemoveVar = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
                result = json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:u"]))
                self.assertFalse(result["success"])
                self.assertEqual(result["removed_variables"], 0)
                self.assertEqual(result["already_absent_variables"], 0)
                self.assertEqual(result["failed_variables"], 1)
                self.assertEqual(result["results"][0]["failed"], ["m:u"])
                self.assertNotIn("already absent", result["message"])
                self.assertEqual(columns, {("Bus 1", "m:u")})

    def test_remove_keeps_partial_changes_across_multiple_monitors(self):
        bus = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        for outcome in (RuntimeError("remove failed"), 2, 1):
            with self.subTest(outcome=outcome):
                result_file, _ = self._result_recording_app([bus], {("Bus 1", "m:u")})
                broken = FakeObject("Second", "IntMon", "Second.IntMon", {"obj_id": bus})
                broken.NVars = Mock(return_value=1)
                broken.GetVar = Mock(return_value="m:u")
                broken.RemoveVar = Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
                result_file.GetContents.return_value.append(broken)
                result = json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:u"]))
                self.assertEqual(result["removed_variables"], 1)
                self.assertEqual(result["already_absent_variables"], 0)
                self.assertEqual(result["failed_variables"], int(outcome != 1))
                self.assertEqual(result["success"], outcome == 1)
                self.assertIn("rerun contingency analysis", result["message"])

    def test_recording_tools_report_monitor_errors_once_and_keep_healthy_changes(self):
        good = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        bad = FakeObject("Bus 2", "ElmTerm", "Grid/Bus 2.ElmTerm")
        other = FakeObject("Bus 3", "ElmTerm", "Grid/Bus 3.ElmTerm")
        for function in (mcp_module.add_contingency_result_variables, mcp_module.remove_contingency_result_variables):
            for failing_read in ("NVars", "GetVar"):
                with self.subTest(function=function.__name__, read=failing_read):
                    result_file, _ = self._result_recording_app([good, bad, other], {
                        ("Bus 1", "m:u"), ("Bus 2", "m:u"), ("Bus 3", "m:u"),
                    })
                    monitors = result_file.GetContents.return_value
                    setattr(monitors[1], failing_read, Mock(side_effect=RuntimeError("broken monitor")))
                    variable = "m:phiu" if function is mcp_module.add_contingency_result_variables else "m:u"
                    result = json.loads(function("*.ElmTerm", [variable]))
                    self.assertFalse(result["success"])
                    self.assertEqual(len(result["errors"]), 1)
                    self.assertEqual(result["errors"][0]["monitor_index"], 1)
                    self.assertEqual(result["errors"][0]["object_full_name"], bad.GetFullName())
                    self.assertEqual(result["failed_variables"], 1)
                    changed = "added_variables" if function is mcp_module.add_contingency_result_variables else "removed_variables"
                    self.assertEqual(result[changed], 2)
                    result_file.GetContents.assert_called_once_with("*.IntMon", 1)
                    self.assertEqual(monitors[0].attribute_reads.count("obj_id"), 1)
                    self.assertEqual(monitors[2].attribute_reads.count("obj_id"), 1)

    def test_unknown_monitor_targets_never_claim_absence_or_add_duplicates(self):
        buses = [FakeObject(f"Bus {i}", "ElmTerm", f"Grid/Bus {i}.ElmTerm") for i in range(3)]
        for function in (mcp_module.add_contingency_result_variables, mcp_module.remove_contingency_result_variables):
            for failure in ("obj_id", "GetFullName", "class_selection"):
                with self.subTest(function=function.__name__, failure=failure):
                    result_file, _ = self._result_recording_app(buses, set())
                    target = FakeObject("Bus 0", "ElmTerm", "Grid/Bus 0.ElmTerm")
                    monitor = FakeObject("Unknown", "IntMon", "Unknown.IntMon", {
                        "obj_id": None if failure == "class_selection" else target,
                        "className": "",
                    })
                    monitor.NVars = Mock(return_value=1)
                    monitor.GetVar = Mock(return_value="m:u")
                    monitor.RemoveVar = Mock()
                    if failure == "obj_id":
                        monitor.GetAttribute = Mock(side_effect=RuntimeError("unreadable target"))
                    elif failure == "GetFullName":
                        target.GetFullName = Mock(side_effect=RuntimeError("unreadable target name"))
                    result_file.GetContents.return_value.append(monitor)
                    result = json.loads(function("*.ElmTerm", ["m:u"]))
                    self.assertFalse(result["success"])
                    self.assertEqual(len(result["errors"]), 1)
                    self.assertEqual(result["failed_variables"], 3)
                    self.assertEqual(result["configured_objects"], 0)
                    result_file.AddVariable.assert_not_called()
                    monitor.RemoveVar.assert_not_called()
                    if function is mcp_module.remove_contingency_result_variables:
                        self.assertEqual(result["already_absent_variables"], 0)
                    if failure == "class_selection":
                        self.assertIn("class/group selections", result["errors"][0]["message"])

    def test_class_recording_is_recognized_and_object_removal_is_protected(self):
        bus = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        result_file, columns = self._result_recording_app([bus], {("Bus 1", "m:u")})
        object_monitor = result_file.GetContents.return_value[0]
        class_monitor = FakeObject("Terminal", "IntMon", "Terminal.IntMon", {
            "obj_id": None, "className": "ElmTerm",
        })
        class_monitor.NVars = Mock(return_value=1)
        class_monitor.GetVar = Mock(return_value="m:u")
        class_monitor.RemoveVar = Mock()
        result_file.GetContents.return_value.append(class_monitor)

        added = json.loads(mcp_module.add_contingency_result_variables(
            "*.ElmTerm", ["m:u", "m:phiu"],
        ))
        self.assertTrue(added["success"])
        self.assertEqual(added["already_recorded_variables"], 1)
        self.assertEqual(added["added_variables"], 1)
        result_file.AddVariable.assert_called_once_with(bus, "m:phiu")

        blocked = json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:u"]))
        self.assertFalse(blocked["success"])
        self.assertEqual(blocked["failed_variables"], 1)
        self.assertEqual(blocked["already_absent_variables"], 0)
        self.assertEqual(blocked["removed_variables"], 0)
        self.assertIn("class-level ElmTerm", blocked["errors"][0]["message"])
        object_monitor.RemoveVar.assert_not_called()
        class_monitor.RemoveVar.assert_not_called()
        self.assertIn(("Bus 1", "m:u"), columns)

        for expected in ("removed_variables", "already_absent_variables"):
            removed = json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:phiu"]))
            self.assertTrue(removed["success"])
            self.assertEqual(removed[expected], 1)
        restored = json.loads(mcp_module.add_contingency_result_variables("*.ElmTerm", ["m:phiu"]))
        self.assertTrue(restored["success"])
        self.assertEqual(restored["added_variables"], 1)
        class_monitor.RemoveVar.assert_not_called()

    def test_class_only_and_unrelated_class_selections(self):
        bus = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        for class_name in ("ElmTerm", "ElmLne"):
            with self.subTest(class_name=class_name):
                result_file, _ = self._result_recording_app([bus], set())
                monitor = FakeObject("Class", "IntMon", "Class.IntMon", {
                    "obj_id": None, "className": class_name,
                })
                monitor.NVars = Mock(return_value=1)
                monitor.GetVar = Mock(return_value="m:u")
                monitor.RemoveVar = Mock()
                result_file.GetContents.return_value.append(monitor)
                result = json.loads(mcp_module.add_contingency_result_variables("*.ElmTerm", ["m:u"]))
                self.assertTrue(result["success"])
                self.assertEqual(result["already_recorded_variables"], int(class_name == "ElmTerm"))
                self.assertEqual(result["added_variables"], int(class_name != "ElmTerm"))
                monitor.RemoveVar.assert_not_called()

    def test_remove_counts_only_objects_with_matching_selections(self):
        buses = [FakeObject(f"Bus {i}", "ElmTerm", f"Grid/Bus {i}.ElmTerm") for i in range(3)]
        result_file, _ = self._result_recording_app(buses, {("Bus 0", "m:u")})
        target = result_file.GetContents.return_value[0].GetAttribute("obj_id")
        self.assertIsNot(target, buses[0])
        result = json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:u"]))
        self.assertTrue(result["success"])
        self.assertEqual(result["configured_objects"], 1)
        self.assertEqual(result["objects_without_selection"], 2)
        self.assertEqual(result["removed_variables"], 1)
        self.assertEqual(result["already_absent_variables"], 2)

    def test_missing_screening_booleans_are_unknown(self):
        command = FakeObject("Contingency Analysis", "ComSimoutage", "Contingency Analysis.ComSimoutage", {"scrCritSimple": 0})
        app = Mock()
        app.GetActiveStudyCase.return_value = object()
        app.GetFromStudyCase.return_value = command
        FakeAgent._shared_app = app
        settings = json.loads(mcp_module.get_contingency_configuration())["settings"]
        self.assertIs(settings["simple_loading_criterion"], False)
        for name in ("combined_loading_criterion", "ignore_base_case_overloads", "screen_only_recorded_elements"):
            self.assertIsNone(settings[name])

    def test_recording_tools_keep_string_schema_and_reject_numeric_entries(self):
        from typing import get_type_hints
        from pydantic import TypeAdapter, ValidationError
        for function in (mcp_module.add_contingency_result_variables, mcp_module.remove_contingency_result_variables):
            with self.subTest(function=function.__name__):
                adapter = TypeAdapter(get_type_hints(function)["variables"])
                self.assertEqual(adapter.json_schema()["items"], {"type": "string"})
                with self.assertRaises(ValidationError):
                    adapter.validate_python(["m:u", 7])
                result = json.loads(function("*.ElmTerm", ["m:u", "   "]))
                self.assertFalse(result["success"])
                self.assertIn("indexes 1", result["message"])

    def test_recording_tools_share_validation_and_context_errors(self):
        for kwargs in ({"calculation_method": "other"}, {"max_objects": "oops"}, {"object_query": ""}):
            with self.subTest(kwargs=kwargs):
                arguments = {"object_query": "*.ElmTerm", "variables": ["m:u"], **kwargs}
                self.assertEqual(
                    json.loads(mcp_module.add_contingency_result_variables(**arguments)),
                    json.loads(mcp_module.remove_contingency_result_variables(**arguments)),
                )
        good = FakeObject("Bus 1", "ElmTerm", "Grid/Bus 1.ElmTerm")
        self._result_recording_app([good], set())
        FakeAgent._shared_app.GetActiveStudyCase.return_value = None
        self.assertEqual(
            json.loads(mcp_module.add_contingency_result_variables("*.ElmTerm", ["m:u"])),
            json.loads(mcp_module.remove_contingency_result_variables("*.ElmTerm", ["m:u"])),
        )

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
