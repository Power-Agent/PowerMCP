"""PSS/E server tools against a fake psspy.

PSS/E is commercial and Windows only, so CI never has it. These tests stand in
a fake engine for the parts of the server that are plain Python: what a tool
does with the error codes psspy hands back. The live-engine counterparts are in
PSSE/tests and skip themselves without an installation.
"""

from __future__ import annotations

import pytest

from PSSE import psse_mcp


class FakePsspy:
    """Records calls; each method returns what the test configured."""

    def __init__(self, case=0, abuscount=(0, 23), abrncount=(0, 34), amachcount=(0, 6)):
        self.calls = []
        self._returns = {
            "case": case,
            "abuscount": abuscount,
            "abrncount": abrncount,
            "amachcount": amachcount,
        }

    def __getattr__(self, name):
        if name not in self._returns:
            raise AttributeError(name)

        def call(*args, **kwargs):
            self.calls.append(name)
            return self._returns[name]

        return call


@pytest.fixture
def case_file(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    path = tmp_path / "savnw.sav"
    path.write_bytes(b"")
    return path


def _use(monkeypatch, fake):
    monkeypatch.setattr(psse_mcp, "psspy", fake)
    monkeypatch.setattr(psse_mcp, "_ensure_psse", lambda: fake)


def test_open_case_returns_the_counts_of_the_loaded_case(monkeypatch, case_file):
    fake = FakePsspy()
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result == {
        "status": "success",
        "case_info": {
            "path": str(case_file),
            "num_buses": 23,
            "num_branches": 34,
            "num_generators": 6,
        },
    }


def test_open_case_reports_a_failed_load_instead_of_the_previous_case(
    monkeypatch, case_file
):
    """psspy.case leaves the previous case in memory when it fails.

    Counting after a failed load describes that earlier case, so the tool used
    to report success with another network's sizes under the new path.
    """
    fake = FakePsspy(case=3)
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result["status"] == "error"
    assert result["ierr"] == 3
    assert "psspy.case" in result["message"]
    assert fake.calls == ["case"]


@pytest.mark.parametrize("failing", ["abuscount", "abrncount", "amachcount"])
def test_open_case_reports_whichever_count_fails(monkeypatch, case_file, failing):
    fake = FakePsspy(**{failing: (1, None)})
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result["status"] == "error"
    assert result["ierr"] == 1
    assert f"psspy.{failing}" in result["message"]
