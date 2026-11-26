import unittest
from unittest.mock import Mock, patch

from PowerFactory.Agent_DIgSILENT import DIgSILENTAgent


class ProjectActivationTest(unittest.TestCase):
    def setUp(self):
        DIgSILENTAgent._shared_app = None
        DIgSILENTAgent._shared_project = None
        DIgSILENTAgent._shared_project_path = None

    def tearDown(self):
        DIgSILENTAgent._shared_app = None
        DIgSILENTAgent._shared_project = None
        DIgSILENTAgent._shared_project_path = None

    def test_activate_project_reuses_application_and_verifies_active_project(self):
        project = Mock()
        project.GetAttribute.return_value = "first-project"
        project.GetFullName.return_value = r"\pf-user\first-project.IntPrj"
        study_case = Mock()
        study_case.GetAttribute.return_value = "Study Case"
        study_case.GetFullName.return_value = (
            r"\pf-user\first-project.IntPrj\Study Case.IntCase"
        )
        app = Mock()
        app.ActivateProject.return_value = 0
        app.GetActiveProject.return_value = project
        app.GetActiveStudyCase.return_value = study_case

        with patch.object(
            DIgSILENTAgent,
            "_get_application",
            return_value=app,
        ) as get_application:
            result = DIgSILENTAgent.activate_project("first-project")

        self.assertTrue(result["success"])
        self.assertEqual(result["name"], "first-project")
        self.assertEqual(
            result["full_name"],
            r"\pf-user\first-project.IntPrj",
        )
        self.assertEqual(result["study_case"], "Study Case")
        self.assertEqual(
            result["study_case_full_name"],
            r"\pf-user\first-project.IntPrj\Study Case.IntCase",
        )
        get_application.assert_called_once_with(open_digsilent=False)
        app.ActivateProject.assert_called_once_with("first-project")
        app.GetActiveProject.assert_called_once_with()
        app.GetActiveStudyCase.assert_called_once_with()
        self.assertIs(DIgSILENTAgent._shared_project, project)
        self.assertEqual(DIgSILENTAgent._shared_project_path, "first-project")

    def test_activate_project_handles_integer_success_return_value(self):
        app = Mock()
        app.ActivateProject.return_value = 0
        project = Mock()
        project.GetAttribute.return_value = "first-project"
        project.GetFullName.return_value = r"\pf-user\first-project.IntPrj"
        study_case = Mock()
        study_case.GetAttribute.return_value = "Study Case"
        study_case.GetFullName.return_value = r"\pf-user\first-project.IntPrj\Study Case.IntCase"
        app.GetActiveProject.return_value = project
        app.GetActiveStudyCase.return_value = study_case

        with patch.object(DIgSILENTAgent, "_get_application", return_value=app):
            result = DIgSILENTAgent.activate_project("first-project")

        self.assertTrue(result["success"])
        app.GetActiveProject.assert_called_once_with()

    def test_activate_project_reports_nonzero_integer_failure(self):
        app = Mock()
        app.ActivateProject.return_value = 1

        with patch.object(DIgSILENTAgent, "_get_application", return_value=app):
            result = DIgSILENTAgent.activate_project("first-project")

        self.assertFalse(result["success"])
        self.assertIn("status code 1", result["message"])
        app.GetActiveProject.assert_not_called()

    def test_activate_project_reports_api_failure(self):
        app = Mock()
        app.ActivateProject.side_effect = RuntimeError("database unavailable")

        with patch.object(DIgSILENTAgent, "_get_application", return_value=app):
            result = DIgSILENTAgent.activate_project("first-project")

        self.assertFalse(result["success"])
        self.assertIn("Project activation failed: database unavailable", result["message"])

    def test_activate_project_reports_verification_mismatch(self):
        active_project = Mock()
        active_project.GetAttribute.return_value = "other-project"
        active_project.GetFullName.return_value = r"\pf-user\other-project.IntPrj"
        app = Mock()
        app.ActivateProject.return_value = 0
        app.GetActiveProject.return_value = active_project

        with patch.object(DIgSILENTAgent, "_get_application", return_value=app):
            result = DIgSILENTAgent.activate_project("first-project")

        self.assertFalse(result["success"])
        self.assertIn("activated a different project", result["message"])

    def test_activate_project_rejects_blank_name(self):
        result = DIgSILENTAgent.activate_project("  ")

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "project_name cannot be empty")


if __name__ == "__main__":
    unittest.main()
