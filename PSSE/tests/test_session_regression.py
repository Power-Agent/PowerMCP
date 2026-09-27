"""PSS/E MCP session and error-recovery regression tests.

These tests exercise the PowerMCP PSS/E tool handlers through realistic
operation sequences. They are skipped automatically when PSS/E or the
validation case is unavailable.

Run locally on a licensed PSS/E installation:

    py -3.14 -m pytest PSSE/tests/test_session_regression.py -v -s
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pytest


CASE = Path(
    os.environ.get(
        "PSSE_VALIDATION_CASE",
        str(Path(__file__).resolve().parents[1] / "savnw.sav"),
    )
)


def _server():
    """Import the MCP server without eagerly importing PSS/E."""
    from PSSE import psse_mcp

    return psse_mcp


def _require_psse():
    """Return the MCP server after confirming PSS/E is available."""
    psse_mcp = _server()
    try:
        psse_mcp._ensure_psse()
    except Exception as exc:
        pytest.skip(f"PSS/E is not available: {exc}")
    return psse_mcp


@pytest.fixture
def psse():
    """Provide the PSS/E MCP server for regression tests."""
    return _require_psse()


@pytest.fixture
def case():
    """Provide the local validation case."""
    if not CASE.exists():
        pytest.skip(
            "PSS/E validation case not available; "
            "set PSSE_VALIDATION_CASE"
        )
    return str(CASE.resolve())


def test_open_solve_query_sequence(psse: Any, case: str):
    """Opening, solving, and querying a case should work as one sequence."""
    opened = psse.open_case(case)

    assert opened["status"] == "success", opened
    assert opened["case_info"]["num_buses"] > 0
    assert opened["case_info"]["num_branches"] > 0
    assert opened["case_info"]["num_generators"] > 0

    solved = psse.solve_case()

    assert solved["status"] == "success", solved
    assert solved["ierr"] == 0

    queried = psse.run_psspy_command(
        "abusreal",
        {"sid": -1, "flag": 2, "string": ["PU"]},
    )

    assert queried["status"] == "success", queried
    assert queried["ierr"] == 0
    assert len(queried["rarray"]) > 0


def test_repeated_solve_and_query(psse: Any, case: str):
    """Repeated solve/query operations should remain numerically stable."""
    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    first_solve = psse.solve_case()
    assert first_solve["status"] == "success", first_solve
    assert first_solve["ierr"] == 0

    first_query = psse.run_psspy_command(
        "abusreal",
        {"sid": -1, "flag": 2, "string": ["PU"]},
    )
    assert first_query["status"] == "success", first_query
    assert first_query["ierr"] == 0

    second_solve = psse.solve_case()
    assert second_solve["status"] == "success", second_solve
    assert second_solve["ierr"] == 0

    second_query = psse.run_psspy_command(
        "abusreal",
        {"sid": -1, "flag": 2, "string": ["PU"]},
    )
    assert second_query["status"] == "success", second_query
    assert second_query["ierr"] == 0

    first_values = first_query["rarray"]
    second_values = second_query["rarray"]

    assert len(first_values) == len(second_values)

    for first_row, second_row in zip(first_values, second_values):
        assert len(first_row) == len(second_row)

        for first_value, second_value in zip(first_row, second_row):
            assert math.isclose(
                first_value,
                second_value,
                rel_tol=1e-6,
                abs_tol=1e-5,
            )


def test_invalid_command_does_not_break_session(psse: Any, case: str):
    """An invalid command should return an error without breaking the session."""
    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    invalid = psse.run_psspy_command(
        "this_command_does_not_exist",
        {},
    )

    assert invalid["status"] == "error", invalid

    solved = psse.solve_case()

    assert solved["status"] == "success", solved
    assert solved["ierr"] == 0


def test_invalid_arguments_do_not_break_session(psse: Any, case: str):
    """An invalid command argument should not poison the PSS/E session."""
    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    invalid = psse.run_psspy_command(
        "abusreal",
        {
            "sid": "invalid",
            "flag": 2,
            "string": ["PU"],
        },
    )

    assert invalid["status"] == "error", invalid

    valid = psse.run_psspy_command(
        "abusreal",
        {
            "sid": -1,
            "flag": 2,
            "string": ["PU"],
        },
    )

    assert valid["status"] == "success", valid
    assert valid["ierr"] == 0
    assert len(valid["rarray"]) > 0


def test_invalid_case_does_not_break_session(psse: Any, case: str):
    """A failed case-open operation should not prevent later valid use."""
    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    invalid = psse.open_case(
        str(Path(case).with_name("does_not_exist.sav"))
    )

    assert invalid["status"] == "error", invalid

    solved = psse.solve_case()

    assert solved["status"] == "success", solved
    assert solved["ierr"] == 0

    queried = psse.run_psspy_command(
        "abusreal",
        {"sid": -1, "flag": 2, "string": ["PU"]},
    )

    assert queried["status"] == "success", queried
    assert queried["ierr"] == 0


def test_lookup_and_search_remain_available_after_operations(
    psse: Any,
    case: str,
):
    """Command discovery tools should remain usable during a session."""
    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    solved = psse.solve_case()
    assert solved["status"] == "success", solved

    lookup = psse.lookup_psspy_command("abusreal")

    assert lookup.get("function_name") == "abusreal"

    search = psse.search_psspy_commands("bus")

    assert search["status"] == "success", search
    assert search["count"] >= 0
