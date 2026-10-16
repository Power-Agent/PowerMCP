import os
import tempfile
import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module


class FakePage:
    def __init__(self, name):
        self.name = name

    def GetAttribute(self, attribute):
        if attribute != "loc_name":
            raise KeyError(attribute)
        return self.name


class FakeGraphicsBoard:
    def __init__(self, pages):
        self.pages = pages
        self.shown = []

    def GetContents(self, pattern):
        if pattern != "*.SetDeskpage":
            raise AssertionError(pattern)
        return self.pages

    def Show(self, page):
        self.shown.append(page)
        return 0


class FakeExportCommand:
    def __init__(self):
        self.attributes = {}
        self.execute_calls = 0

    def SetAttribute(self, name, value):
        self.attributes[name] = value

    def Execute(self):
        self.execute_calls += 1
        with open(self.attributes["f"], "wb") as output:
            output.write(b"%PDF-1.7\n")
        return 0


class FakeApplication:
    def __init__(self, pages, active_project=True, active_case=True):
        self.project = object() if active_project else None
        self.study_case = object() if active_case else None
        self.board = FakeGraphicsBoard(pages)
        self.command = FakeExportCommand()
        self.current_diagram = None

    def GetCurrentDiagram(self):
        return self.current_diagram

    def GetActiveProject(self):
        return self.project

    def GetActiveStudyCase(self):
        return self.study_case

    def GetGraphicsBoard(self):
        return self.board

    def GetFromStudyCase(self, class_name):
        if class_name != "ComWr":
            raise AssertionError(class_name)
        return self.command


class GridPdfExportTest(unittest.TestCase):
    def run_export(self, app, output, diagram_name=""):
        with patch.object(
            agent_module,
            "checked_path",
            side_effect=lambda path, **_: path,
        ), patch.object(
            agent_module.DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ), patch.object(
            agent_module.log,
            "ok",
        ), patch.object(
            agent_module.log,
            "error",
        ):
            return agent_module.DIgSILENTAgent.export_active_grid_pdf(
                output,
                diagram_name,
                open_digsilent=False,
            )

    def test_exports_only_available_diagram_as_pdf(self):
        page = FakePage("Summary Grid")
        app = FakeApplication([page])

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "active-grid.pdf")
            success, message = self.run_export(app, output)

            self.assertTrue(success, message)
            self.assertTrue(os.path.isfile(output))

        self.assertEqual(app.board.shown, [page])
        self.assertEqual(app.command.attributes["iopt_rd"], "pdf")
        self.assertEqual(app.command.attributes["iopt_savas"], 0)
        self.assertEqual(app.command.execute_calls, 1)

    def test_selects_requested_diagram_by_exact_name(self):
        overview = FakePage("Overview")
        summary = FakePage("Summary Grid")
        app = FakeApplication([overview, summary])

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "summary.pdf")
            success, message = self.run_export(
                app,
                output,
                diagram_name="Summary Grid",
            )

        self.assertTrue(success, message)
        self.assertEqual(app.board.shown, [summary])

    def test_restores_previous_diagram_after_success_and_failure(self):
        previous = FakePage("Previously open diagram")
        selected = FakePage("Export Grid")
        for fails in (False, True):
            with self.subTest(export_fails=fails):
                app = FakeApplication([selected])
                app.current_diagram = previous
                with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
                    output = os.path.join(directory, "grid.pdf")
                    if fails:
                        with patch.object(app.command, "Execute", side_effect=RuntimeError("export failed")):
                            success, message = self.run_export(app, output)
                    else:
                        success, message = self.run_export(app, output)
                self.assertEqual(success, not fails, message)
                self.assertEqual(app.board.shown, [selected, previous])

    def test_reports_restoration_failure(self):
        selected = FakePage("Export Grid")
        app = FakeApplication([selected])
        app.current_diagram = FakePage("Previously open diagram")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            with patch.object(app.board, "Show", side_effect=[0, 1]):
                success, message = self.run_export(app, os.path.join(directory, "grid.pdf"))
        self.assertFalse(success)
        self.assertIn("restore previous diagram", message)

    def test_requires_name_when_multiple_diagrams_are_available(self):
        app = FakeApplication([FakePage("Overview"), FakePage("Summary Grid")])

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "grid.pdf")
            success, message = self.run_export(app, output)

        self.assertFalse(success)
        self.assertIn("provide diagram_name", message)
        self.assertIn("Overview", message)
        self.assertIn("Summary Grid", message)
        self.assertEqual(app.command.execute_calls, 0)

    def test_requires_active_project(self):
        app = FakeApplication([FakePage("Summary Grid")], active_project=False)

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "grid.pdf")
            success, message = self.run_export(app, output)

        self.assertFalse(success)
        self.assertEqual(message, "No PowerFactory project is active")
        self.assertEqual(app.command.execute_calls, 0)

    def test_rejects_existing_destination_without_opening_powerfactory(self):
        app = FakeApplication([FakePage("Summary Grid")])

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "grid.pdf")
            with open(output, "wb") as existing:
                existing.write(b"existing")
            success, message = self.run_export(app, output)

        self.assertFalse(success)
        self.assertIn("already exists", message)
        self.assertEqual(app.command.execute_calls, 0)

    def test_requires_pdf_extension(self):
        app = FakeApplication([FakePage("Summary Grid")])

        with tempfile.TemporaryDirectory(dir=os.path.dirname(__file__)) as directory:
            output = os.path.join(directory, "grid.png")
            success, message = self.run_export(app, output)

        self.assertFalse(success)
        self.assertEqual(message, "file_path must end with .pdf")
        self.assertEqual(app.command.execute_calls, 0)


if __name__ == "__main__":
    unittest.main()
