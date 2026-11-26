"""Regression tests for output-path containment in ``hope_read_output``."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.core import hope_read_output  # noqa: E402


def _create_case_tree(root: Path) -> Path:
    case_dir = root / "ModelCases" / "test_case"
    output_dir = case_dir / "output"
    output_dir.mkdir(parents=True)
    settings_dir = case_dir / "Settings"
    settings_dir.mkdir(parents=True)
    (settings_dir / "HOPE_model_settings.yml").write_text(
        "model_mode: GTEP\nsolver: highs\n",
        encoding="utf-8",
    )

    with (output_dir / "system_cost.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cost"])
        writer.writeheader()
        writer.writerow({"cost": "42"})

    subdirectory = output_dir / "postprocess_snapshot"
    subdirectory.mkdir()
    with (subdirectory / "metadata.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["key", "value"])
        writer.writeheader()
        writer.writerow({"key": "version", "value": "1"})
    return root / "ModelCases"


class OutputPathContainmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        modelcases = _create_case_tree(root)
        self.environment = mock.patch.dict(
            "os.environ",
            {
                "HOPE_REPO_ROOT": str(root),
                "HOPE_MODELCASES_PATH": str(modelcases),
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_normal_filename_succeeds(self) -> None:
        result = hope_read_output(case_id="test_case", filename="system_cost.csv")
        self.assertTrue(result["ok"], result)

    def test_contained_subdirectory_succeeds(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="postprocess_snapshot/metadata.csv",
        )
        self.assertTrue(result["ok"], result)

    def test_parent_traversal_is_blocked(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="../../etc/passwd",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")

    def test_normalized_parent_traversal_is_blocked(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="postprocess_snapshot/../../Settings/HOPE_model_settings.yml",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")

    def test_absolute_path_is_blocked(self) -> None:
        result = hope_read_output(case_id="test_case", filename="/etc/passwd")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")


if __name__ == "__main__":
    unittest.main()
