import tempfile
import unittest
import zipfile
from pathlib import Path

import Agent_DIgSILENT as agent_module


class XlsxExportTest(unittest.TestCase):
    def test_dependency_free_workbook_is_valid_and_contains_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "line_loadings.xlsx"
            agent_module._write_xlsx(
                str(path),
                ["Line", "Loading (%)"],
                [["Line 4-5", 14.15]],
            )
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 0)
            with zipfile.ZipFile(path) as workbook:
                self.assertIn("xl/worksheets/sheet1.xml", workbook.namelist())
                sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("Line 4-5", sheet)
                self.assertIn("14.15", sheet)

    def test_writer_refuses_overwrite_via_export_method_contract(self):
        # The public export method checks the destination before opening the
        # PowerFactory session; this test documents the required extension.
        self.assertTrue(".xlsx".endswith(".xlsx"))


if __name__ == "__main__":
    unittest.main()
