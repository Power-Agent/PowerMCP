import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psse_mcp


def test_dynamic_output_missing_file():
    result = psse_mcp.list_dynamic_output_channels(
        os.path.join(os.path.dirname(__file__), "does_not_exist.out")
    )

    assert result["status"] == "error"
    assert "does not exist" in result["message"]


def test_dynamic_output_read_missing_file():
    result = psse_mcp.read_dynamic_output(
        os.path.join(os.path.dirname(__file__), "does_not_exist.out")
    )

    assert result["status"] == "error"
    assert "does not exist" in result["message"]


@pytest.mark.skipif(
    not os.environ.get("PSSE_DYNAMIC_OUTPUT"),
    reason="Set PSSE_DYNAMIC_OUTPUT to run the PSS/E integration test",
)
def test_dynamic_output_real_file():
    outfile = os.environ["PSSE_DYNAMIC_OUTPUT"]

    result = psse_mcp.list_dynamic_output_channels(outfile)

    assert result["status"] == "success"
    assert result["channels"]["time"] == "Time(s)"
    assert len(result["channels"]) == 7

    result = psse_mcp.read_dynamic_output(
        outfile,
        channels=[1, 2],
    )

    assert result["status"] == "success"
    assert result["num_points"] == 123
    assert result["channels"]["1"] == "POWR 101[NUC-A 21.600]1"
    assert result["channels"]["2"] == "POWR 102[NUC-B 21.600]1"
    assert len(result["data"]["time"]) == 123
    assert len(result["data"]["1"]) == 123
    assert len(result["data"]["2"]) == 123

    result = psse_mcp.read_dynamic_output(
        outfile,
        channels=[],
    )

    assert result["status"] == "error"
    assert "at least one channel" in result["message"]

    result = psse_mcp.read_dynamic_output(
        outfile,
        channels=[0],
    )

    assert result["status"] == "error"
    assert "positive integer channel numbers" in result["message"]

    result = psse_mcp.read_dynamic_output(
        outfile,
        channels=[True],
    )

    assert result["status"] == "error"
    assert "positive integer channel numbers" in result["message"]

    result = psse_mcp.read_dynamic_output(
        outfile,
        channels=[99],
    )

    assert result["status"] == "error"
    assert "not found" in result["message"]
