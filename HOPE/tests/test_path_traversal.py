"""Tests for CWE-22 path traversal mitigation in hope_read_output."""
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


def _create_case_tree(tmp: Path) -> Path:
    """Build a minimal ModelCases/<case>/output/ tree for testing."""
    case_dir = tmp / "ModelCases" / "test_case"
    output_dir = case_dir / "output"
    output_dir.mkdir(parents=True)
    settings_dir = case_dir / "Settings"
    settings_dir.mkdir(parents=True)
    (settings_dir / "HOPE_model_settings.yml").write_text(
        "model_mode: GTEP\nsolver: highs\n"
    )
    # Write a small CSV so legitimate reads succeed
    csv_path = output_dir / "system_cost.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["cost"])
        writer.writeheader()
        writer.writerow({"cost": "42"})
    # Also put a subdir CSV for subdirectory-access test
    sub = output_dir / "postprocess_snapshot"
    sub.mkdir()
    sub_csv = sub / "metadata.csv"
    with sub_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "value"])
        writer.writeheader()
        writer.writerow({"key": "version", "value": "1"})
    return tmp


class TestPathTraversal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        tmp = Path(self.tmpdir_obj.name)
        _create_case_tree(tmp)
        self.env_patch = mock.patch.dict(
            "os.environ",
            {"HOPE_REPO_ROOT": str(tmp)},
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.tmpdir_obj.cleanup()

    # ---- Legitimate reads should still work ----

    def test_normal_filename_succeeds(self) -> None:
        result = hope_read_output(case_id="test_case", filename="system_cost.csv")
        self.assertTrue(result["ok"], result)

    def test_subdirectory_filename_succeeds(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="postprocess_snapshot/metadata.csv",
        )
        self.assertTrue(result["ok"], result)

    # ---- Path traversal attempts MUST be blocked ----

    def test_dot_dot_traversal_is_blocked(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="../../etc/passwd",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")

    def test_dot_dot_within_subdir_is_blocked(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="postprocess_snapshot/../../Settings/HOPE_model_settings.yml",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")

    def test_absolute_path_is_blocked(self) -> None:
        result = hope_read_output(
            case_id="test_case",
            filename="/etc/passwd",
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_type"], "path_traversal")

    def test_encoded_dot_dot_not_normalised_away(self) -> None:
        # Depending on OS normalisation this might just be file-not-found,
        # but must never succeed as a file read outside the output dir.
        result = hope_read_output(
            case_id="test_case",
            filename="..%2F..%2Fetc%2Fpasswd",
        )
        # Acceptable outcomes: path_traversal error OR file_not_found —
        # NOT a successful read.
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
