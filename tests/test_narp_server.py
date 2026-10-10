from __future__ import annotations

import importlib.util
from pathlib import Path

from NARP.narp_mcp import REQUIRED_FILES, parse_output, validate_input_dir


def test_required_inputs_are_complete(tmp_path):
    for name in REQUIRED_FILES:
        p = tmp_path / name
        if name == "LEEI":
            p.mkdir()
        else:
            p.write_text("x", encoding="utf-8")

    result = validate_input_dir(str(tmp_path))
    assert result["valid"] is True
    assert set(result["required_files"]) == set(REQUIRED_FILES)


def test_validate_input_reports_pipeline_files(tmp_path):
    (tmp_path / "ZZTC.csv").write_text("x", encoding="utf-8")
    result = validate_input_dir(str(tmp_path))
    assert result["valid"] is False
    assert {"ZZFC.csv", "ZZOD.csv", "ZZDD.csv", "LEEI"} <= set(result["missing"])


def test_parser_keeps_table12_remarks_and_table13_sd(tmp_path):
    path = tmp_path / "output.txt"
    path.write_text(
        """
TABLE 12
  1  GC       1.00   2.00   3   4.00  5.00
  1  TC       6.00   7.00   8   9.00  10.00
  1  GT      11.00  12.00  13  14.00  15.00
  1  AV      16.00  17.00  18  19.00  20.00

TABLE 13
  A1         100         120         20         1.5      4.0        5.0      2.5      6.0      3.5
  A2         200         250         25         2.0      7.0        8.0      4.0      9.0      5.0
  AV         300         400         10         3.0      9.0        10.0     5.0      12.0     6.0
""",
        encoding="utf-8",
    )
    result = parse_output(str(path))
    assert [row["remark"] for row in result["table_12"]] == ["GC", "TC", "GT", "AV"]
    assert result["summary"]["A1"]["HLOLE"] == 1.5
    assert result["summary"]["A1"]["HLOLE_pct_sd"] == 4.0
    assert result["summary"]["A1"]["EUE"] == 5.0
    assert result["summary"]["A1"]["EUE_pct_sd"] == 2.5
    assert result["summary"]["A1"]["LOLE"] == 6.0
    assert result["summary"]["A1"]["LOLE_pct_sd"] == 3.5
    assert result["pool"][0]["label"] == "AV"


def test_narp_engine_is_not_imported_at_server_startup():
    assert "reliabilityassessment.monte_carlo.narpMain" not in __import__("sys").modules


def test_narp_child_is_a_function_call():
    source = Path("NARP/narp_mcp.py").read_text(encoding="utf-8")
    assert "from reliabilityassessment.monte_carlo.narpMain import narpMain" in source
    assert "narpMain(sys.argv[1])" in source
