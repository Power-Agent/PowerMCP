"""PSS/E MCP end-to-end dynamic simulation regression test."""

from __future__ import annotations

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

OUTPUT = Path(__file__).resolve().parents[1] / "powermcp_dynamic_test.out"


def _server():
    from PSSE import psse_mcp

    return psse_mcp


def _require_psse():
    psse_mcp = _server()
    try:
        psse_mcp._ensure_psse()
    except Exception as exc:
        pytest.skip(f"PSS/E is not available: {exc}")
    return psse_mcp


@pytest.fixture
def psse():
    return _require_psse()


@pytest.fixture
def case():
    if not CASE.exists():
        pytest.skip(
            "PSS/E validation case not available; "
            "set PSSE_VALIDATION_CASE"
        )
    return str(CASE.resolve())


def test_end_to_end_dynamic_simulation(psse: Any, case: str):
    """Run and validate a one-second PSS/E dynamic simulation."""

    if OUTPUT.exists():
        OUTPUT.unlink()

    opened = psse.open_case(case)
    assert opened["status"] == "success", opened

    solved = psse.run_psspy_command("fdns", {})
    assert solved["status"] == "success", solved
    assert solved["ierr"] == 0

    result = psse.run_psspy_command("cong", {"opt": 0})
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "conl",
        {
            "sid": 0,
            "all": 1,
            "apiopt": 1,
            "status": [1, 0],
            "loadin": [0, 0, 0, 0],
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "conl",
        {
            "sid": 0,
            "all": 1,
            "apiopt": 2,
            "status": [1, 0],
            "loadin": [100, 0, 100, 0],
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "conl",
        {
            "sid": 0,
            "all": 1,
            "apiopt": 3,
            "status": [1, 0],
            "loadin": [0, 0, 0, 0],
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command("ordr", {"opt": 0})
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command("fact", {})
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command("tysl", {"opt": 0})
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "dyre_new",
        {
            "startindx": [1, 1, 1, 1],
            "dyrefile": str(
                Path(__file__).resolve().parents[1] / "savnw.dyr"
            ),
            "conecfile": "",
            "conetfile": "",
            "compilfil": "",
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "chsb",
        {
            "sid": 0,
            "all": 1,
            "status": [-1, -1, -1, 1, 2, 0],
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "strt",
        {
            "option": 0,
            "outfile": str(OUTPUT),
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    result = psse.run_psspy_command(
        "run",
        {
            "option": 0,
            "tpause": 1.0,
            "nprt": 1,
            "nplt": 1,
            "crtplt": 1,
        },
    )
    assert result["status"] == "success", result
    assert result["ierr"] == 0

    assert OUTPUT.exists()
    assert OUTPUT.stat().st_size > 0

    import dyntools

    ch = dyntools.CHNF(str(OUTPUT), outvrsn=0)
    title, channels, data = ch.get_data()

    assert title
    assert channels["time"] == "Time(s)"

    dynamic_channels = [
        key for key in channels if key != "time"
    ]

    assert len(dynamic_channels) == 6
    assert len(data["time"]) > 1
    assert data["time"][0] < 0
    assert data["time"][-1] >= 1.0 - 1e-5

    for key in dynamic_channels:
        assert len(data[key]) == len(data["time"])

    assert channels[1] == "POWR 101[NUC-A 21.600]1"
    assert channels[2] == "POWR 102[NUC-B 21.600]1"
    assert channels[3] == "POWR 206[URBGEN 18.000]1"
    assert channels[4] == "POWR 211[HYDRO_G 20.000]1"
    assert channels[5] == "POWR 3011[MINE_G 13.800]1"
    assert channels[6] == "POWR 3018[CATDOG_G 13.800]1"

    OUTPUT.unlink(missing_ok=True)