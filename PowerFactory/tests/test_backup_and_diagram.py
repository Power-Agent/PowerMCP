import os
import tempfile
import unittest
from unittest.mock import patch

import Agent_DIgSILENT as agent_module


class Command:
    def __init__(self): self.attrs = {}
    def SetAttribute(self, key, value): self.attrs[key] = value
    def Execute(self):
        with open(self.attrs["g_file"], "wb") as handle: handle.write(b"PFD")
        return 0


class BackupApp:
    def __init__(self, project): self.project, self.command = project, Command()
    def GetActiveProject(self): return self.project
    def GetFromStudyCase(self, name): self.assert_name = name; return self.command
    def GetCalcRelevantObjects(self, query): return [self.project.grid]


class Obj:
    def __init__(self, name, cls="ElmTerm"): self.loc_name, self.cls, self.graphics, self.attrs, self.parent = name, cls, [], {}, None
    def GetClassName(self): return self.cls
    def GetFullName(self): return (self.parent.GetFullName() + "\\" if self.parent else "\\") + self.loc_name
    def SetAttribute(self, key, value): self.attrs[key] = value
    def GetAttribute(self, key): return self.attrs[key]
    def CreateObject(self, cls, name):
        obj=Obj(name, cls); obj.parent = self; self.graphics.append(obj); return obj
    def GetParent(self): return self.parent
    def GetContents(self, pattern, *_): return self.graphics if pattern == "*.IntGrf" else []


class Grid(Obj):
    def __init__(self): super().__init__("SENI_Study_Model", "ElmNet"); self.objects=[]
    def GetContents(self, pattern, *_): return self.objects


class Project(Obj):
    def __init__(self, grid): super().__init__("first-project", "IntPrj"); self.grid=grid; self.created=[]
    def GetCalcRelevantObjects(self, query): return [self.grid]
    def GetContents(self, pattern, *_): return self.created
    def CreateObject(self, cls, name):
        obj=Obj(name, cls); self.created.append(obj); return obj


class DiagramParent(Obj):
    def __init__(self, project):
        super().__init__("Diagrams", "IntPrjfolder"); self.project = project
    def CreateObject(self, cls, name):
        obj = Obj(name, cls); obj.parent = self; obj.GetParent = lambda: self; self.project.created.append(obj); return obj


class ExistingDiagram(Obj):
    def __init__(self, parent): super().__init__("Existing", "IntGrfnet"); self.parent = parent
    def GetParent(self): return self.parent


class BackupDiagramTests(unittest.TestCase):
    def test_backup_refuses_overwrite_and_verifies_file(self):
        project=Project(Grid()); app=BackupApp(project)
        with tempfile.TemporaryDirectory() as directory:
            path=os.path.join(directory,"case.pfd")
            with patch.object(agent_module.DIgSILENTAgent,"_get_application",return_value=app), patch.object(agent_module,"checked_path",side_effect=lambda p,**_:p):
                result=agent_module.DIgSILENTAgent.export_project_backup(path)
                self.assertTrue(result["success"])
                duplicate=agent_module.DIgSILENTAgent.export_project_backup(path)
                self.assertFalse(duplicate["success"])

    def test_diagram_is_new_and_references_existing_objects(self):
        grid=Grid(); grid.objects=[Obj("Bus", "ElmTerm"), Obj("Line", "ElmLne")]
        project=Project(grid)
        project.created.append(ExistingDiagram(DiagramParent(project)))
        with patch.object(agent_module.DIgSILENTAgent,"_get_application",return_value=BackupApp(project)):
            result=agent_module.DIgSILENTAgent.create_network_diagram("first-project","SENI_Study_Model","New SLD")
        self.assertTrue(result["success"], result)
        self.assertEqual(result["graphics"], 2)


if __name__ == "__main__": unittest.main()
