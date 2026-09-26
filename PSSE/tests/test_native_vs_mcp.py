"""Native PSS/E API vs PowerMCP PSS/E validation.

This test compares the values returned by the native PSS/E Python API with
the values returned by the PowerMCP PSS/E tool handlers for the same case.

It is intentionally skipped when PSS/E or the validation case is unavailable,
so the normal open-source CI suite is not made dependent on a commercial
installation.

Run locally on a licensed PSS/E installation, for example:

    py -3.14 -m pytest PSSE/tests/test_native_vs_mcp.py -v

Or run this file directly:

    py -3.14 PSSE/tests/test_native_vs_mcp.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest


CASE = Path(
    os.environ.get(
        "PSSE_VALIDATION_CASE",
        str(Path(__file__).resolve().parents[2] / "savnw.sav"),
    )
)


def _server():
    """Import the MCP server without eagerly importing PSS/E."""
    from PSSE import psse_mcp

    return psse_mcp


def _numeric_values(value: Any) -> list[float]:
    """Flatten a PSS/E numeric return value into comparable floats."""
    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, (list, tuple)):
        result: list[float] = []
        for item in value:
            result.extend(_numeric_values(item))
        return result

    return [float(value)]


def _compare_arrays(
    name: str,
    native: Any,
    mcp: Any,
    *,
    atol: float = 1.0e-5,
) -> float:
    native_values = _numeric_values(native)
    mcp_values = _numeric_values(mcp)

    assert len(native_values) == len(mcp_values), (
        f"{name}: length mismatch: "
        f"native={len(native_values)}, mcp={len(mcp_values)}"
    )

    max_diff = max(
        (abs(a - b) for a, b in zip(native_values, mcp_values)),
        default=0.0,
    )

    assert max_diff <= atol, (
        f"{name}: maximum difference {max_diff:.6e} exceeds "
        f"absolute tolerance {atol:.6e}"
    )
    return max_diff


@pytest.mark.skipif(
    not CASE.exists(),
    reason="PSS/E validation case not available; set PSSE_VALIDATION_CASE",
)
def test_native_psse_matches_powermcp():
    """Compare native PSS/E results with PowerMCP results."""
    psse_mcp = _server()

    try:
        psspy = psse_mcp._ensure_psse()
    except Exception as exc:
        pytest.skip(f"PSS/E is not available: {exc}")

    case = str(CASE.resolve())

    # ------------------------------------------------------------------
    # 1. Native PSS/E path
    # ------------------------------------------------------------------
    ierr = psspy.case(case)
    assert ierr == 0, f"native psspy.case failed with ierr={ierr}"

    ierr = psspy.nsol()
    assert ierr == 0, f"native psspy.nsol failed with ierr={ierr}"

    native_bus_ierr, native_bus = psspy.abusreal(
        sid=-1, flag=2, string=["PU"]
    )
    native_gen_ierr, native_gen = psspy.amachreal(
        sid=-1, flag=4, string=["PGEN", "QGEN"]
    )
    native_branch_ierr, native_branch = psspy.aflowreal(
        sid=-1,
        owner=1,
        ties=1,
        flag=1,
        string=["P", "Q", "MVA"],
    )

    assert native_bus_ierr == 0
    assert native_gen_ierr == 0
    assert native_branch_ierr == 0

    # ------------------------------------------------------------------
    # 2. PowerMCP path
    # ------------------------------------------------------------------
    open_result = psse_mcp.open_case(case)
    assert open_result["status"] == "success", open_result

    solve_result = psse_mcp.solve_case()
    assert solve_result["status"] == "success", solve_result
    assert solve_result["ierr"] == 0

    mcp_bus_result = psse_mcp.run_psspy_command(
        "abusreal",
        {"sid": -1, "flag": 2, "string": ["PU"]},
    )
    mcp_gen_result = psse_mcp.run_psspy_command(
        "amachreal",
        {"sid": -1, "flag": 4, "string": ["PGEN", "QGEN"]},
    )
    mcp_branch_result = psse_mcp.run_psspy_command(
        "aflowreal",
        {
            "sid": -1,
            "owner": 1,
            "ties": 1,
            "flag": 1,
            "string": ["P", "Q", "MVA"],
        },
    )

    assert mcp_bus_result["status"] == "success", mcp_bus_result
    assert mcp_gen_result["status"] == "success", mcp_gen_result
    assert mcp_branch_result["status"] == "success", mcp_branch_result

    # ------------------------------------------------------------------
    # 3. Native-vs-MCP numerical equivalence
    # ------------------------------------------------------------------
    bus_diff = _compare_arrays(
        "bus voltage PU",
        native_bus,
        mcp_bus_result["rarray"],
    )
    gen_diff = _compare_arrays(
        "generator PGEN/QGEN",
        native_gen,
        mcp_gen_result["rarray"],
    )
    branch_diff = _compare_arrays(
        "branch P/Q/MVA",
        native_branch,
        mcp_branch_result["rarray"],
    )

    print("\nNative PSS/E vs PowerMCP validation")
    print("-----------------------------------")
    print(f"Case: {case}")
    print(f"Bus values:    {len(_numeric_values(native_bus))}")
    print(f"Generator values: {len(_numeric_values(native_gen))}")
    print(f"Branch values: {len(_numeric_values(native_branch))}")
    print(f"Max bus difference:    {bus_diff:.6e}")
    print(f"Max generator difference: {gen_diff:.6e}")
    print(f"Max branch difference:   {branch_diff:.6e}")
    print("RESULT: PASS")


if __name__ == "__main__":
    try:
        test_native_psse_matches_powermcp()
    except pytest.skip.Exception as exc:
        print(f"SKIP: {exc}")
        raise SystemExit(0)
