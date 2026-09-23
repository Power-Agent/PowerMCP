import unittest
from fnmatch import fnmatchcase
from unittest.mock import Mock, call, patch

import Agent_DIgSILENT as agent_module


DEFAULTS = {
    "ElmTerm": {"uknom": 0.0, "outserv": 0},
    "StaCubic": {"obj_id": None},
    "StaSwitch": {"aUsage": "", "on_off": 0},
    "ElmLod": {"bus1": None, "plini": 0.0, "qlini": 0.0, "outserv": 0},
    "ElmSym": {
        "typ_id": None,
        "bus1": None,
        "pgini": 0.0,
        "qgini": 0.0,
        "outserv": 0,
    },
    "ElmLne": {
        "typ_id": None,
        "bus1": None,
        "bus2": None,
        "dline": 0.0,
        "outserv": 0,
    },
    "ElmTr2": {
        "typ_id": None,
        "bushv": None,
        "buslv": None,
        "outserv": 0,
    },
    "EvtSwitch": {
        "p_target": None,
        "time": 0.0,
        "i_switch": 0,
        "outserv": 0,
    },
}


class FakeObject:
    def __init__(self, parent, class_name, name):
        self.parent = parent
        self.class_name = class_name
        self.attributes = {"loc_name": name, **DEFAULTS.get(class_name, {})}
        self.objects = {}
        self.reject_attribute = None
        self.content_queries = []

    def __getitem__(self, class_name):
        return self.objects.setdefault(class_name, [])

    def GetAttribute(self, name):
        return self.attributes[name]

    def SetAttribute(self, name, value):
        root = self
        while root.parent is not None:
            root = root.parent
        if name != root.reject_attribute:
            self.attributes[name] = value
            if (
                name in {"bus1", "bus2", "bushv", "buslv"}
                and value is not None
            ):
                value.SetAttribute("obj_id", self)

    def GetClassName(self):
        return self.class_name

    def GetFullName(self):
        prefix = self.parent.GetFullName() if self.parent else r"\user"
        return f"{prefix}\\{self.attributes['loc_name']}.{self.class_name}"

    def GetParent(self):
        return self.parent

    def GetContents(self, query, recursive):
        self.content_queries.append(query)
        if query == "*":
            return [
                obj
                for objects in self.objects.values()
                for obj in objects
            ]
        name_pattern, class_name = query.rsplit(".", 1)
        return [
            obj for obj in self[class_name]
            if fnmatchcase(str(obj.GetAttribute("loc_name")), name_pattern)
        ]

    def CreateObject(self, class_name, name):
        obj = FakeObject(self, class_name, name[:40])
        self[class_name].append(obj)
        return obj

    def Delete(self):
        for name in ("bus1", "bus2", "bushv", "buslv"):
            cubicle = self.attributes.get(name)
            if cubicle is not None:
                cubicle.SetAttribute("obj_id", None)
        self.parent[self.class_name].remove(self)


class FakeApplication:
    def __init__(self, grids, objects=None):
        self.grids = grids
        self.objects = objects or {}
        self.shown = None

    def GetCalcRelevantObjects(self, query):
        if query == "*.ElmNet":
            return self.grids
        return list(self.objects.get(query, []))

    def GetActiveProject(self):
        if not hasattr(self, "project"):
            self.project = FakeObject(None, "IntPrj", "Project")
        return self.project

    def Show(self):
        self.shown = True

    def Hide(self):
        self.shown = False


class FakePowerFactory:
    def __init__(self, app):
        self.app = app

    def GetApplicationExt(self):
        return self.app


class ComponentCreationTest(unittest.TestCase):
    def test_run_contingency_analysis_uses_configured_command(self):
        command = Mock()
        command.Execute.return_value = 0
        command.GetClassName.return_value = "ComSimoutage"
        command.GetFullName.return_value = (
            r"\user\test\Case 1\Contingency Analysis.ComSimoutage"
        )
        values = {
            "loc_name": "Contingency Analysis",
            "dat_src": "MAN",
            "iopt_method": 1,
            "iopt_Linear": 0,
            "dynamicCase": 0,
        }
        command.GetAttribute.side_effect = values.__getitem__

        app = Mock()
        app.GetActiveStudyCase.return_value = Mock()
        app.GetFromStudyCase.return_value = command
        self.use_application(app)

        result = agent_module.DIgSILENTAgent.run_contingency_analysis(
            open_digsilent=False,
        )

        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["execution_code"], 0)
        self.assertEqual(result["command"]["class_name"], "ComSimoutage")
        command.Execute.assert_called_once_with()
        command.HasResults.assert_not_called()
        command.SetAttribute.assert_not_called()
        app.GetFromStudyCase.assert_called_once_with("ComSimoutage")

    def test_run_contingency_analysis_reports_native_failure_code(self):
        command = Mock()
        command.Execute.return_value = 2
        command.GetClassName.return_value = "ComSimoutage"
        command.GetFullName.return_value = (
            r"\user\test\Case 1\Contingency Analysis.ComSimoutage"
        )
        values = {
            "loc_name": "Contingency Analysis",
            "dat_src": "MAN",
            "iopt_method": 1,
            "iopt_Linear": 0,
            "dynamicCase": 0,
        }
        command.GetAttribute.side_effect = values.__getitem__

        app = Mock()
        app.GetActiveStudyCase.return_value = Mock()
        app.GetFromStudyCase.return_value = command
        self.use_application(app)

        result = agent_module.DIgSILENTAgent.run_contingency_analysis(
            open_digsilent=False,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["execution_code"], 2)
        self.assertIn("2", result["message"])
        self.assertEqual(result["command"]["class_name"], "ComSimoutage")
        self.assertEqual(result["settings"]["calculation_method"], 1)

    def test_run_contingency_analysis_sets_explicit_calculation_method(self):
        modes = {
            "ac": 0,
            "dc": 1,
            "ac_linearised": 2,
            "linearised_screening": 3,
        }

        for mode, expected in modes.items():
            with self.subTest(mode=mode):
                values = {
                    "loc_name": "Contingency Analysis",
                    "dat_src": "MAN",
                    "iopt_method": 0,
                    "iopt_Linear": 0,
                    "copt_Linear": 0,
                    "iACDCCombine": 0,
                    "dynamicCase": 0,
                }
                command = Mock()
                command.Execute.return_value = 0
                command.GetClassName.return_value = "ComSimoutage"
                command.GetFullName.return_value = "Contingency Analysis.ComSimoutage"
                command.GetAttribute.side_effect = values.__getitem__
                command.SetAttribute.side_effect = values.__setitem__

                app = Mock()
                app.GetActiveStudyCase.return_value = Mock()
                app.GetFromStudyCase.return_value = command
                self.use_application(app)

                result = agent_module.DIgSILENTAgent.run_contingency_analysis(
                    open_digsilent=False,
                    calculation_method=mode,
                )

                self.assertTrue(result["success"], result["message"])
                self.assertEqual(result["settings"]["mode"], mode)
                self.assertEqual(result["settings"]["linear_method"], expected)
                self.assertEqual(values["iopt_Linear"], 0)
                self.assertEqual(command.SetAttribute.call_args_list, [
                    call("iopt_Linear", expected),
                    call("iopt_Linear", 0),
                ])
                command.Execute.assert_called_once_with()

    def test_run_contingency_analysis_restores_method_after_exception(self):
        values = {
            "loc_name": "Contingency Analysis",
            "iopt_Linear": 2,
        }
        command = Mock()
        command.Execute.side_effect = RuntimeError("native failure")
        command.GetAttribute.side_effect = values.__getitem__
        command.SetAttribute.side_effect = values.__setitem__

        app = Mock()
        app.GetActiveStudyCase.return_value = Mock()
        app.GetFromStudyCase.return_value = command
        self.use_application(app)

        result = agent_module.DIgSILENTAgent.run_contingency_analysis(
            open_digsilent=False,
            calculation_method="dc",
        )

        self.assertFalse(result["success"])
        self.assertIn("native failure", result["message"])
        self.assertEqual(values["iopt_Linear"], 2)
        self.assertEqual(command.SetAttribute.call_args_list, [
            call("iopt_Linear", 1),
            call("iopt_Linear", 2),
        ])

    def test_run_contingency_analysis_rejects_unknown_method(self):
        result = agent_module.DIgSILENTAgent.run_contingency_analysis(
            open_digsilent=False,
            calculation_method="unknown",
        )

        self.assertFalse(result["success"])
        self.assertIn("calculation_method must be one of", result["message"])

    def test_create_contingency_is_idempotent(self):
        app = FakeApplication([])
        project = app.GetActiveProject()
        folder = project.CreateObject("IntFltcases", "Fault Cases")
        target = FakeObject(None, "ElmLne", "Line 01 - 02")
        app.objects["Line 01 - 02.ElmLne"] = [target]
        self.use_application(app)

        first = agent_module.DIgSILENTAgent.create_contingency(
            "MCP N-1 Test",
            "Line 01 - 02.ElmLne",
            open_digsilent=False,
        )
        second = agent_module.DIgSILENTAgent.create_contingency(
            "MCP N-1 Test",
            "Line 01 - 02.ElmLne",
            open_digsilent=False,
        )

        self.assertTrue(first["success"], first["message"])
        self.assertTrue(first["created"])
        self.assertTrue(second["success"], second["message"])
        self.assertFalse(second["created"])
        case = folder["IntEvt"][0]
        self.assertEqual(len(case["EvtSwitch"]), 1)
        self.assertIs(case["EvtSwitch"][0].GetAttribute("p_target"), target)

    def test_create_contingency_rejects_existing_event_with_other_settings(self):
        app = FakeApplication([])
        folder = app.GetActiveProject().CreateObject("IntFltcases", "Fault Cases")
        target = FakeObject(None, "ElmLne", "Line 01 - 02")
        app.objects["Line 01 - 02.ElmLne"] = [target]
        self.use_application(app)

        first = agent_module.DIgSILENTAgent.create_contingency(
            "MCP N-1 Test",
            "Line 01 - 02.ElmLne",
            action="open",
            open_digsilent=False,
        )
        second = agent_module.DIgSILENTAgent.create_contingency(
            "MCP N-1 Test",
            "Line 01 - 02.ElmLne",
            action="close",
            open_digsilent=False,
        )

        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertIn("different settings", second["message"])
        self.assertEqual(len(folder["IntEvt"][0]["EvtSwitch"]), 1)

    def test_create_contingency_preserves_error_when_rollback_fails(self):
        app = FakeApplication([])
        app.GetActiveProject().CreateObject("IntFltcases", "Fault Cases")
        app.GetActiveProject().reject_attribute = "p_target"
        target = FakeObject(None, "ElmLne", "Line 01 - 02")
        app.objects["Line 01 - 02.ElmLne"] = [target]
        self.use_application(app)

        with patch.object(
            FakeObject,
            "Delete",
            side_effect=RuntimeError("cleanup failed"),
        ) as delete:
            result = agent_module.DIgSILENTAgent.create_contingency(
                "MCP N-1 Test",
                "Line 01 - 02.ElmLne",
                open_digsilent=False,
            )

        self.assertFalse(result["success"])
        self.assertIn("p_target", result["message"])
        self.assertEqual(delete.call_count, 2)

    def test_set_and_verify_attributes_falls_back_to_attribute_name(self):
        element = FakeObject(None, "ElmTerm", "Bus")
        element.attributes["custom_attribute"] = 0
        element.reject_attribute = "custom_attribute"

        with self.assertRaisesRegex(RuntimeError, "custom_attribute"):
            agent_module.DIgSILENTAgent._set_and_verify_attributes(
                element,
                {"custom_attribute": 1},
                "Bus",
            )

    def setUp(self):
        self.original_pf = agent_module.pf
        self.original_app = agent_module.DIgSILENTAgent._shared_app

    def tearDown(self):
        agent_module.pf = self.original_pf
        agent_module.DIgSILENTAgent._shared_app = self.original_app

    def use_application(self, app):
        agent_module.pf = FakePowerFactory(app)
        agent_module.DIgSILENTAgent._shared_app = None

    def network(self, bus_names=(), template=None):
        grid = FakeObject(None, "ElmNet", "Grid")
        buses = {
            name: grid.CreateObject("ElmTerm", name)
            for name in bus_names
        }
        objects = {}
        template_object = template_type = None
        if template:
            query, class_name, type_class = template
            template_type = FakeObject(None, type_class, "Test Type")
            template_object = grid.CreateObject(
                class_name,
                query.rsplit(".", 1)[0],
            )
            template_object.SetAttribute("typ_id", template_type)
            objects[query] = [template_object]
        self.use_application(FakeApplication([grid], objects))
        return grid, buses, template_object, template_type

    def assert_failed(self, result, text):
        if isinstance(result, dict):
            ok = result["success"]
            message = result["message"]
        else:
            ok, message = result
        self.assertFalse(ok)
        self.assertIn(text, message)
        return message

    def assert_attributes(self, obj, expected):
        for name, value in expected.items():
            self.assertEqual(obj.GetAttribute(name), value)

    def add_component(self, component_type, component_name, parameters, **kwargs):
        return agent_module.DIgSILENTAgent.add_component(
            component_type,
            component_name,
            parameters,
            **kwargs,
        )

    def test_add_component_updates_active_diagram(self):
        grid, _, _, _ = self.network()
        app = agent_module.pf.app

        with patch.object(
            agent_module.DIgSILENTAgent,
            "_update_active_diagram",
        ) as update_diagram:
            ok, message = self.add_component(
                "bus",
                "Graphical Test Bus",
                {"nominal_voltage_kv": 110.0},
                open_digsilent=False,
                update_graphics=True,
            )

        self.assertTrue(ok, message)
        update_diagram.assert_called_once_with(
            app,
            grid["ElmTerm"][0],
            )
        self.assertIn("graphics=updated", message)
        self.assertEqual(len(grid["ElmTerm"]), 1)

        with patch.object(
            agent_module.DIgSILENTAgent,
            "_update_active_diagram",
            side_effect=RuntimeError("layout failed"),
        ):
            ok, message = self.add_component(
                "bus",
                "Graphical Failure Bus",
                {"nominal_voltage_kv": 110.0},
                open_digsilent=False,
                update_graphics=True,
            )

        self.assertFalse(ok)
        self.assertIn("was created, but graphical update failed", message)
        self.assertIn("layout failed", message)
        self.assertEqual(len(grid["ElmTerm"]), 2)
        self.assertEqual(
            grid["ElmTerm"][-1].GetAttribute("loc_name"),
            "Graphical Failure Bus",
        )

    def test_update_active_diagram_uses_automatic_insertion(self):
        app = Mock()
        desktop = Mock()
        layout = Mock()

        component = FakeObject(
            None,
            "ElmTerm",
            "Graphical Test Bus",
        )
        layout.Execute.return_value = 0
        app.GetDesktop.return_value = desktop
        app.GetFromStudyCase.return_value = layout

        with patch.object(
            agent_module.DIgSILENTAgent,
            "_find_component_graphics",
            return_value=[Mock()],
        ) as find_graphics:
            agent_module.DIgSILENTAgent._update_active_diagram(
                app,
                component,
            )

        desktop.Unfreeze.assert_called_once_with()
        desktop.Freeze.assert_called_once_with()
        app.Rebuild.assert_called_once_with()
        self.assertEqual(layout.iAction, 1)
        self.assertEqual(layout.insertionMode, 1)
        find_graphics.assert_called_once_with(app, component)
        app.GetFromStudyCase.assert_called_once_with("ComSgllayout")
        layout.GetAttribute.assert_not_called()

    def test_update_active_diagram_preserves_original_error(self):
        app = Mock()
        desktop = Mock()
        layout = Mock()
        component = Mock()

        app.GetDesktop.return_value = desktop
        app.GetFromStudyCase.return_value = layout
        layout.Execute.side_effect = RuntimeError("layout failed")
        desktop.Freeze.side_effect = RuntimeError("restore failed")

        with self.assertRaisesRegex(RuntimeError, "layout failed"):
            agent_module.DIgSILENTAgent._update_active_diagram(
                app,
                component,
            )

        desktop.Unfreeze.assert_called_once_with()
        desktop.Freeze.assert_called_once_with()

    def test_update_active_diagram_requires_layout_tool(self):
        app = Mock()
        app.GetDesktop.return_value = Mock()
        app.GetFromStudyCase.return_value = None

        with self.assertRaisesRegex(
            RuntimeError,
            "Diagram Layout Tool is unavailable",
        ):
            agent_module.DIgSILENTAgent._update_active_diagram(
                app,
                Mock(),
            )

        app.GetFromStudyCase.assert_called_once_with("ComSgllayout")

    def test_add_component_bus_validation_and_rollback(self):
        grid, _, _, _ = self.network()
        ok, message = self.add_component(
            "bus",
            "MCP Test Bus",
            {"nominal_voltage_kv": 110.0},
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assert_attributes(
            grid["ElmTerm"][0],
            {"uknom": 110.0, "outserv": 0},
        )

        self.assert_failed(
            self.add_component(
                "bus",
                "MCP Test Bus",
                {"nominal_voltage_kv": 110.0},
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            self.add_component(
                "bus",
                "Invalid Bus",
                {"nominal_voltage_kv": -1.0},
                open_digsilent=False,
            ),
            "finite positive",
        )
        self.assertEqual(len(grid["ElmTerm"]), 1)

        grid_a = FakeObject(None, "ElmNet", "Grid A")
        grid_b = FakeObject(None, "ElmNet", "Grid B")
        self.use_application(FakeApplication([grid_a, grid_b]))
        self.assert_failed(
            self.add_component(
                "bus",
                "Ambiguous Bus",
                {"nominal_voltage_kv": 20.0},
                open_digsilent=False,
            ),
            "Multiple grids",
        )
        ok, message = self.add_component(
            "bus",
            "Selected Bus",
            {"nominal_voltage_kv": 20.0},
            grid_name="Grid B",
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(grid_a["ElmTerm"], [])
        self.assertEqual(grid_b["ElmTerm"][0].GetAttribute("outserv"), 1)

        failing_grid, _, _, _ = self.network()
        failing_grid.reject_attribute = "uknom"
        self.assert_failed(
            self.add_component(
                "bus",
                "Rollback Bus",
                {"nominal_voltage_kv": 110.0},
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmTerm"], [])

    def test_add_component_load_validation_and_rollback(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        bus = buses["Bus 01"]
        ok, message = self.add_component(
            "load",
            "MCP Test Load",
            {
                "bus_name": "Bus 01",
                "active_power_mw": 50.0,
                "reactive_power_mvar": 12.5,
            },
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmLod"][0]
        self.assertIs(created.GetAttribute("bus1"), bus["StaCubic"][0])
        self.assert_attributes(
            created,
            {"plini": 50.0, "qlini": 12.5, "outserv": 1},
        )

        self.assert_failed(
            self.add_component(
                "load",
                "MCP Test Load",
                {"bus_name": "Bus 01", "active_power_mw": 50.0},
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            self.add_component(
                "load",
                "Missing Bus Load",
                {"bus_name": "Unknown Bus", "active_power_mw": 10.0},
                open_digsilent=False,
            ),
            "Bus not found",
        )
        self.assert_failed(
            self.add_component(
                "load",
                "Invalid Load",
                {"bus_name": "Bus 01", "active_power_mw": -1.0},
                open_digsilent=False,
            ),
            "finite and non-negative",
        )

        failing_grid, buses, _, _ = self.network(("Bus 01",))
        failing_grid.reject_attribute = "plini"
        self.assert_failed(
            self.add_component(
                "load",
                "Rollback Load",
                {"bus_name": "Bus 01", "active_power_mw": 10.0},
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmLod"], [])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])

    def test_add_component_generator_validation_and_rollback(self):
        template = ("G 01.ElmSym", "ElmSym", "TypSym")
        grid, buses, template_object, machine_type = self.network(
            ("Bus 01",), template
        )
        ok, message = self.add_component(
            "generator",
            "MCP Test Generator",
            {
                "bus_name": "Bus 01",
                "template_generator": template[0],
                "active_power_mw": 25.0,
                "reactive_power_mvar": 5.0,
            },
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmSym"][1]
        self.assertIs(created.GetAttribute("typ_id"), machine_type)
        self.assertIs(
            created.GetAttribute("bus1"), buses["Bus 01"]["StaCubic"][0]
        )
        self.assert_attributes(
            created,
            {"pgini": 25.0, "qgini": 5.0, "outserv": 1},
        )

        self.assert_failed(
            self.add_component(
                "generator",
                "MCP Test Generator",
                {
                    "bus_name": "Bus 01",
                    "template_generator": template[0],
                    "active_power_mw": 25.0,
                },
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            self.add_component(
                "generator",
                "Missing Template Generator",
                {
                    "bus_name": "Bus 01",
                    "template_generator": "Unknown.ElmSym",
                    "active_power_mw": 10.0,
                },
                open_digsilent=False,
            ),
            "Template generator not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 01",), template
        )
        failing_grid.reject_attribute = "pgini"
        self.assert_failed(
            self.add_component(
                "generator",
                "Rollback Generator",
                {
                    "bus_name": "Bus 01",
                    "template_generator": template[0],
                    "active_power_mw": 10.0,
                },
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmSym"], [failing_template])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertIsNotNone(template_object)

    def test_add_component_line_validation_and_rollback(self):
        template = ("Line 01 - 02.ElmLne", "ElmLne", "TypLne")
        grid, buses, _, line_type = self.network(
            ("Bus 01", "Bus 02"), template
        )
        ok, message = self.add_component(
            "line",
            "MCP Test Line",
            {
                "bus1_name": "Bus 01",
                "bus2_name": "Bus 02",
                "template_line": template[0],
                "length_km": 10.0,
            },
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmLne"][1]
        self.assertIs(created.GetAttribute("typ_id"), line_type)
        self.assertIs(
            created.GetAttribute("bus1"), buses["Bus 01"]["StaCubic"][0]
        )
        self.assertIs(
            created.GetAttribute("bus2"), buses["Bus 02"]["StaCubic"][0]
        )

        for bus_name in ("Bus 01", "Bus 02"):
            cubicle = buses[bus_name]["StaCubic"][0]
            switches = cubicle["StaSwitch"]

            self.assertEqual(len(switches), 1)
            self.assert_attributes(
                switches[0],
                {"aUsage": "cbk", "on_off": 1},
            )

        self.assert_attributes(created, {"dline": 10.0, "outserv": 1})

        duplicate = self.add_component(
            "line",
            "MCP Test Line",
            {
                "bus1_name": "Bus 01",
                "bus2_name": "Bus 02",
                "template_line": template[0],
                "length_km": 10.0,
            },
            open_digsilent=False,
        )
        self.assert_failed(duplicate, "already exists")
        self.assert_failed(
            self.add_component(
                "line",
                "Same Bus Line",
                {
                    "bus1_name": "Bus 01",
                    "bus2_name": "Bus 01",
                    "template_line": template[0],
                    "length_km": 10.0,
                },
                open_digsilent=False,
            ),
            "must be different",
        )
        self.assert_failed(
            self.add_component(
                "line",
                "Missing Template Line",
                {
                    "bus1_name": "Bus 01",
                    "bus2_name": "Bus 02",
                    "template_line": "Unknown.ElmLne",
                    "length_km": 10.0,
                },
                open_digsilent=False,
            ),
            "Template line not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 01", "Bus 02"), template
        )
        failing_grid.reject_attribute = "dline"
        self.assert_failed(
            self.add_component(
                "line",
                "Rollback Line",
                {
                    "bus1_name": "Bus 01",
                    "bus2_name": "Bus 02",
                    "template_line": template[0],
                    "length_km": 10.0,
                },
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmLne"], [failing_template])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])

    def test_add_component_transformer_validation_and_rollback(self):
        template = ("Trf 02 - 30.ElmTr2", "ElmTr2", "TypTr2")
        grid, buses, _, transformer_type = self.network(
            ("Bus 02", "Bus 30"), template
        )
        ok, message = self.add_component(
            "transformer",
            "MCP Test Transformer",
            {
                "high_voltage_bus_name": "Bus 02",
                "low_voltage_bus_name": "Bus 30",
                "template_transformer": template[0],
            },
            out_of_service=True,
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        created = grid["ElmTr2"][1]
        self.assertIs(created.GetAttribute("typ_id"), transformer_type)
        self.assertIs(
            created.GetAttribute("bushv"), buses["Bus 02"]["StaCubic"][0]
        )
        self.assertIs(
            created.GetAttribute("buslv"), buses["Bus 30"]["StaCubic"][0]
        )
        self.assertEqual(created.GetAttribute("outserv"), 1)

        self.assert_failed(
            self.add_component(
                "transformer",
                "MCP Test Transformer",
                {
                    "high_voltage_bus_name": "Bus 02",
                    "low_voltage_bus_name": "Bus 30",
                    "template_transformer": template[0],
                },
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assert_failed(
            self.add_component(
                "transformer",
                "Same Bus Transformer",
                {
                    "high_voltage_bus_name": "Bus 02",
                    "low_voltage_bus_name": "Bus 02",
                    "template_transformer": template[0],
                },
                open_digsilent=False,
            ),
            "must be different",
        )
        self.assert_failed(
            self.add_component(
                "transformer",
                "Missing Template Transformer",
                {
                    "high_voltage_bus_name": "Bus 02",
                    "low_voltage_bus_name": "Bus 30",
                    "template_transformer": "Unknown.ElmTr2",
                },
                open_digsilent=False,
            ),
            "Template transformer not found",
        )

        failing_grid, buses, failing_template, _ = self.network(
            ("Bus 02", "Bus 30"), template
        )
        failing_grid.reject_attribute = "typ_id"
        self.assert_failed(
            self.add_component(
                "transformer",
                "Rollback Transformer",
                {
                    "high_voltage_bus_name": "Bus 02",
                    "low_voltage_bus_name": "Bus 30",
                    "template_transformer": template[0],
                },
                open_digsilent=False,
            ),
            "rolled_back=True",
        )
        self.assertEqual(failing_grid["ElmTr2"], [failing_template])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])
        self.assertEqual(buses["Bus 30"]["StaCubic"], [])

    def test_add_component_validation(self):
        self.assert_failed(
            self.add_component(
                "unknown",
                "New Component",
                {},
            ),
            "Unsupported component type",
        )

        self.assert_failed(
            self.add_component(
                "load",
                "New Component",
                {"bus_name": "Bus 01"},
            ),
            "Missing parameter(s)",
        )

        self.assert_failed(
            self.add_component(
                "bus",
                "New Component",
                {
                    "nominal_voltage_kv": 110.0,
                    "bus_name": "Unexpected",
                },
            ),
            "Unsupported parameter(s)",
        )

        self.assert_failed(
            self.add_component(
                "bus",
                "B" * 41,
                {"nominal_voltage_kv": 110.0},
            ),
            "at most 40 characters",
        )

    def test_rollback_uses_retained_cubicle_name(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        grid.reject_attribute = "plini"

        self.assert_failed(
            self.add_component(
                "load",
                "L" * 40,
                {"bus_name": "Bus 01", "active_power_mw": 1.0},
                open_digsilent=False,
            ),
            "rolled_back=True",
        )

        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])

    def test_add_component_parameter_edge_cases(self):
        template = ("G 01.ElmSym", "ElmSym", "TypSym")
        grid, buses, _, _ = self.network(("0",), template)

        ok, message = self.add_component(
            "load",
            "Null Reactive Load",
            {
                "bus_name": 0,
                "active_power_mw": 1.0,
                "reactive_power_mvar": None,
            },
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(grid["ElmLod"][0].GetAttribute("qlini"), 0.0)
        self.assertIs(
            grid["ElmLod"][0].GetAttribute("bus1"),
            buses["0"]["StaCubic"][0],
        )

        ok, message = self.add_component(
            "generator",
            "Null Reactive Generator",
            {
                "bus_name": "0",
                "template_generator": template[0],
                "active_power_mw": 1.0,
                "reactive_power_mvar": None,
            },
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertEqual(grid["ElmSym"][-1].GetAttribute("qgini"), 0.0)

        self.assert_failed(
            self.add_component(
                "load",
                "Boolean Load",
                {"bus_name": "0", "active_power_mw": True},
                open_digsilent=False,
            ),
            "active_power_mw must be a number",
        )
        self.assert_failed(
            self.add_component(
                "bus",
                "Boolean Bus",
                {"nominal_voltage_kv": True},
                open_digsilent=False,
            ),
            "nominal_voltage_kv must be a number",
        )

    def test_delete_component_updates_active_diagram(self):
        grid, buses, _, _ = self.network(("Bus 01",))

        ok, message = self.add_component(
            "load",
            "Graphical Test Load",
            {
                "bus_name": "Bus 01",
                "active_power_mw": 1.0,
                "reactive_power_mvar": 0.25,
            },
            open_digsilent=False,
        )
        self.assertTrue(ok, message)

        app = agent_module.DIgSILENTAgent._shared_app

        project = app.GetActiveProject()
        diagram = project.CreateObject("IntGrfnet", "Grid")

        created_load = grid["ElmLod"][-1]

        target_graphic = diagram.CreateObject(
            "IntGrf",
            "Graphical Test Load Symbol",
        )
        target_graphic.SetAttribute("pDataObj", created_load)

        unrelated_graphic = diagram.CreateObject(
            "IntGrf",
            "Existing Bus Symbol",
        )
        unrelated_graphic.SetAttribute(
            "pDataObj",
            buses["Bus 01"],
        )

        with (
            patch.object(
                app,
                "GetDesktop",
                create=True,
            ) as get_desktop,
            patch.object(
                app,
                "Rebuild",
                return_value=None,
                create=True,
            ) as rebuild,
        ):
            result = agent_module.DIgSILENTAgent.delete_component(
                "load",
                "Graphical Test Load",
                confirmation=f"DELETE load {created_load.GetFullName()}",
                open_digsilent=False,
                update_graphics=True,
            )

        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        get_desktop.assert_not_called()
        rebuild.assert_called_once_with()

        self.assertEqual(result["graphics"]["deleted"], 1)
        self.assertEqual(result["graphics"]["remaining"], [])
        self.assertEqual(result["graphics"]["refresh"], "rebuilt")

        self.assertNotIn(target_graphic, diagram["IntGrf"])
        self.assertIn(unrelated_graphic, diagram["IntGrf"])

        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])

        ok, message = self.add_component(
            "load",
            "Stubborn Graphical Test Load",
            {
                "bus_name": "Bus 01",
                "active_power_mw": 1.0,
                "reactive_power_mvar": 0.25,
            },
            open_digsilent=False,
        )
        self.assertTrue(ok, message)

        stubborn_load = grid["ElmLod"][-1]
        stubborn_graphic = diagram.CreateObject(
            "IntGrf",
            "Stubborn Graphical Test Load Symbol",
        )
        stubborn_graphic.SetAttribute("pDataObj", stubborn_load)

        with (
            patch.object(
                app,
                "GetDesktop",
                create=True,
            ) as get_desktop,
            patch.object(
                stubborn_graphic,
                "Delete",
                side_effect=RuntimeError("graphical deletion blocked"),
            ),
            patch.object(
                app,
                "Rebuild",
                return_value=None,
                create=True,
            ) as rebuild,
        ):
            result = agent_module.DIgSILENTAgent.delete_component(
                "load",
                "Stubborn Graphical Test Load",
                confirmation=f"DELETE load {stubborn_load.GetFullName()}",
                open_digsilent=False,
                update_graphics=True,
            )

        self.assertFalse(result["success"])
        self.assertTrue(result["deleted"])
        self.assertIn("graphical objects remain", result["message"])
        self.assertEqual(result["graphics"]["deleted"], 0)
        self.assertEqual(
            result["graphics"]["remaining"],
            [stubborn_graphic.GetFullName()],
        )
        self.assertEqual(result["graphics"]["refresh"], "rebuilt")
        get_desktop.assert_not_called()
        rebuild.assert_called_once_with()
        self.assertEqual(grid["ElmLod"], [])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertIn(stubborn_graphic, diagram["IntGrf"])

    def test_delete_component_requires_confirmation_and_cleans_connections(self):
        template = ("Line 01 - 02.ElmLne", "ElmLne", "TypLne")
        grid, buses, template_line, _ = self.network(
            ("Bus 01", "Bus 02"), template
        )

        ok, message = self.add_component(
            "line",
            "MCP Test Line",
            {
                "bus1_name": "Bus 01",
                "bus2_name": "Bus 02",
                "template_line": template[0],
                "length_km": 1.0,
            },
            open_digsilent=False,
        )
        self.assertTrue(ok, message)

        result = agent_module.DIgSILENTAgent.delete_component(
            "line",
            "MCP Test Line",
            open_digsilent=False,
        )
        self.assertTrue(result["success"], result["message"])
        self.assertFalse(result["deleted"])
        self.assertIn(
            f"confirmation_required=DELETE line "
            f"{grid['ElmLne'][-1].GetFullName()}",
            result["message"],
        )
        self.assertEqual(len(grid["ElmLne"]), 2)

        self.assert_failed(
            agent_module.DIgSILENTAgent.delete_component(
                "line",
                "MCP Test Line",
                confirmation="DELETE line wrong name",
                open_digsilent=False,
            ),
            "confirmation must exactly match",
        )

        self.assert_failed(
            agent_module.DIgSILENTAgent.delete_component(
                "bus",
                "Bus 01",
                confirmation=(
                    f"DELETE bus {buses['Bus 01'].GetFullName()}"
                ),
                open_digsilent=False,
            ),
            "connected cubicles",
        )

        result = agent_module.DIgSILENTAgent.delete_component(
            "line",
            "MCP Test Line",
            confirmation=(
                f"DELETE line {grid['ElmLne'][-1].GetFullName()}"
            ),
            open_digsilent=False,
        )
        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertEqual(grid["ElmLne"], [template_line])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])
        self.assertEqual(buses["Bus 02"]["StaCubic"], [])

        result = agent_module.DIgSILENTAgent.delete_component(
            "bus",
            "Bus 01",
            confirmation=f"DELETE bus {buses['Bus 01'].GetFullName()}",
            open_digsilent=False,
        )
        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertNotIn(buses["Bus 01"], grid["ElmTerm"])

    def test_delete_component_preserves_protected_cubicle(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        cubicle = buses["Bus 01"].CreateObject(
            "StaCubic",
            "Protected Load Cubicle",
        )
        switch = cubicle.CreateObject("StaSwitch", "Switch")
        switch.SetAttribute("aUsage", "cbk")
        switch.SetAttribute("on_off", 1)
        relay = cubicle.CreateObject("ElmRelay", "Distance Relay")
        load = grid.CreateObject("ElmLod", "Protected Load")
        load.SetAttribute("bus1", cubicle)

        result = agent_module.DIgSILENTAgent.delete_component(
            "load",
            "Protected Load",
            confirmation=f"DELETE load {load.GetFullName()}",
            open_digsilent=False,
        )

        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertIn("preserved_cubicles=1", result["message"])
        self.assertEqual(grid["ElmLod"], [])
        self.assertIn(cubicle, buses["Bus 01"]["StaCubic"])
        self.assertIn(switch, cubicle["StaSwitch"])
        self.assertIn(relay, cubicle["ElmRelay"])

    def test_delete_component_cleans_trimmed_generated_cubicle_name(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        name = "Diagram Automatic Insert Test 20260909B"

        ok, message = self.add_component(
            "load",
            name,
            {"bus_name": "Bus 01", "active_power_mw": 1.0},
            open_digsilent=False,
        )
        self.assertTrue(ok, message)

        cubicle = buses["Bus 01"]["StaCubic"][0]
        cubicle.SetAttribute(
            "loc_name",
            str(cubicle.GetAttribute("loc_name")).rstrip(),
        )
        load = grid["ElmLod"][0]

        result = agent_module.DIgSILENTAgent.delete_component(
            "load",
            name,
            confirmation=f"DELETE load {load.GetFullName()}",
            open_digsilent=False,
        )

        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertNotIn("preserved_cubicles", result["message"])
        self.assertEqual(buses["Bus 01"]["StaCubic"], [])

    def test_delete_bus_ignores_orphan_cubicle(self):
        grid, buses, _, _ = self.network(("Bus 01",))
        bus = buses["Bus 01"]
        bus.CreateObject("StaCubic", "Orphan Cubicle")

        result = agent_module.DIgSILENTAgent.delete_component(
            "bus",
            "Bus 01",
            confirmation=f"DELETE bus {bus.GetFullName()}",
            open_digsilent=False,
        )

        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertNotIn(bus, grid["ElmTerm"])

    def test_named_lookup_handles_case_sensitive_powerfactory_queries(self):
        grid, buses, _, _ = self.network(("Bus 01", "Bus 02"))
        bus = buses["Bus 01"]
        self.assertEqual(grid.GetContents("Bus 01.ElmTerm", 1), [bus])
        self.assertEqual(grid.GetContents("Missing.ElmTerm", 1), [])
        self.assertEqual(
            grid.GetContents("*.ElmTerm", 1), list(buses.values())
        )
        for name in ("bus 01", "BUS 01", "bUS 01"):
            with self.subTest(name=name):
                self.assertEqual(grid.GetContents(f"{name}.ElmTerm", 1), [])
                self.assertEqual(
                    agent_module.DIgSILENTAgent._find_named_contents(
                        grid, name, "ElmTerm"
                    ),
                    [bus],
                )

    def test_add_component_rejects_differently_cased_duplicate(self):
        grid, buses, _, _ = self.network(("bus a",))
        self.assert_failed(
            self.add_component(
                "bus", "Bus A", {"nominal_voltage_kv": 110.0},
                open_digsilent=False,
            ),
            "already exists",
        )
        self.assertEqual(grid["ElmTerm"], [buses["bus a"]])

    def test_add_component_selects_differently_cased_bus(self):
        grid, buses, _, _ = self.network(("Bus 01", "Bus 02"))
        ok, message = self.add_component(
            "load", "Case Test Load",
            {"bus_name": "bus 01", "active_power_mw": 1.0},
            open_digsilent=False,
        )
        self.assertTrue(ok, message)
        self.assertIs(
            grid["ElmLod"][0].GetAttribute("bus1").GetParent(),
            buses["Bus 01"],
        )

    def test_delete_component_uses_retained_name_casing(self):
        grid, buses, _, _ = self.network(("bus a",))

        preview = agent_module.DIgSILENTAgent.delete_component(
            "bus",
            "Bus A",
            open_digsilent=False,
        )

        self.assertTrue(preview["success"], preview["message"])
        self.assertIn(
            f"confirmation_required=DELETE bus "
            f"{buses['bus a'].GetFullName()}",
            preview["message"],
        )

        result = agent_module.DIgSILENTAgent.delete_component(
            "bus",
            "Bus A",
            confirmation=f"DELETE bus {buses['bus a'].GetFullName()}",
            open_digsilent=False,
        )

        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertNotIn(buses["bus a"], grid["ElmTerm"])
        self.assertIn("*.ElmTerm", grid.content_queries)

    def test_delete_confirmation_is_bound_to_grid(self):
        grid_a = FakeObject(None, "ElmNet", "Grid A")
        grid_b = FakeObject(None, "ElmNet", "Grid B")
        load_a = grid_a.CreateObject("ElmLod", "Shared Load")
        load_b = grid_b.CreateObject("ElmLod", "Shared Load")
        self.use_application(FakeApplication([grid_a, grid_b]))

        preview = agent_module.DIgSILENTAgent.delete_component(
            "load",
            "Shared Load",
            grid_name="Grid A",
            open_digsilent=False,
        )
        token_a = f"DELETE load {load_a.GetFullName()}"
        self.assertIn(
            f"confirmation_required={token_a}",
            preview["message"],
        )

        wrong_grid = agent_module.DIgSILENTAgent.delete_component(
            "load",
            "Shared Load",
            grid_name="Grid B",
            confirmation=token_a,
            open_digsilent=False,
        )
        self.assertFalse(wrong_grid["success"])
        self.assertFalse(wrong_grid["deleted"])
        self.assertIn(load_b, grid_b["ElmLod"])

        result = agent_module.DIgSILENTAgent.delete_component(
            "load",
            "Shared Load",
            grid_name="Grid B",
            confirmation=f"DELETE load {load_b.GetFullName()}",
            open_digsilent=False,
        )
        self.assertTrue(result["success"], result["message"])
        self.assertTrue(result["deleted"])
        self.assertNotIn(load_b, grid_b["ElmLod"])


if __name__ == "__main__":
    unittest.main()
