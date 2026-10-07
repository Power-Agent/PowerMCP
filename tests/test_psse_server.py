"""PSS/E server tools against a fake psspy and dyntools.

PSS/E is commercial and Windows only, so CI never has it. These tests stand in
fakes for the parts of the server that are plain Python: what a tool does with
the error codes psspy hands back and the channels dyntools reads. The
live-engine counterparts are in PSSE/tests and skip themselves without an
installation.
"""

from __future__ import annotations

import sys
import types

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


CHANNELS = {
    "time": "Time(s)",
    1: "POWR 101[NUC-A 21.600]1",
    2: "POWR 102[NUC-B 21.600]1",
}
DATA = {
    "time": [-0.0167, 0.0, 0.0083],
    1: [750.0, 750.0, 749.8],
    2: [750.0, 750.0, 749.6],
}


@pytest.fixture
def outfile(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    path = tmp_path / "fault.out"
    path.write_bytes(b"")
    return path


@pytest.fixture
def dyntools(monkeypatch):
    """A fake dyntools that, like the real one, imports only after PSS/E starts.

    dyntools lives in the PSSPY directory, which _ensure_psse puts on sys.path.
    The fake engine start registers the module, so a tool that imports it
    before starting the engine fails here as it does in a fresh session.
    """
    opened = []

    class CHNF:
        def __init__(self, outfile, outvrsn=0):
            opened.append((outfile, outvrsn))

        def get_data(self):
            return "SAVNW FAULT", dict(CHANNELS), {k: list(v) for k, v in DATA.items()}

    module = types.ModuleType("dyntools")
    module.CHNF = CHNF
    module.opened = opened
    module.engine_starts = 0

    def ensure_psse():
        module.engine_starts += 1
        monkeypatch.setitem(sys.modules, "dyntools", module)

    monkeypatch.delitem(sys.modules, "dyntools", raising=False)
    monkeypatch.setattr(psse_mcp, "_ensure_psse", ensure_psse)
    return module


def test_listing_channels_works_in_a_fresh_session(dyntools, outfile):
    result = psse_mcp.list_dynamic_output_channels(str(outfile))

    assert result == {
        "status": "success",
        "outfile": str(outfile),
        "title": "SAVNW FAULT",
        "channels": {
            "time": "Time(s)",
            "1": "POWR 101[NUC-A 21.600]1",
            "2": "POWR 102[NUC-B 21.600]1",
        },
    }
    assert dyntools.opened == [(str(outfile), 0)]


def test_reading_selected_channels_includes_time(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=[2], outvrsn=1)

    assert result["status"] == "success", result
    assert result["channels"] == {"time": "Time(s)", "2": "POWR 102[NUC-B 21.600]1"}
    assert result["data"] == {"time": DATA["time"], "2": DATA[2]}
    assert result["num_points"] == 3
    assert result["total_points"] == 3
    assert result["downsampled"] is False
    assert result["max_points"] == 10_000
    assert dyntools.opened == [(str(outfile), 1)]


def test_reading_without_a_selection_returns_every_channel(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "success", result
    assert set(result["data"]) == {"time", "1", "2"}
    assert result["num_points"] == 3
    assert result["total_points"] == 3
    assert result["downsampled"] is False


def test_reading_dynamic_output_can_be_deterministically_capped(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(
        str(outfile), channels=[1, 2], max_points=2
    )

    assert result["status"] == "success", result
    assert result["num_points"] == 2
    assert result["total_points"] == 3
    assert result["downsampled"] is True
    assert result["max_points"] == 2
    assert result["data"]["time"] == [DATA["time"][0], DATA["time"][-1]]
    assert result["data"]["1"] == [DATA[1][0], DATA[1][-1]]
    assert result["data"]["2"] == [DATA[2][0], DATA[2][-1]]


def test_default_point_cap_bounds_a_large_dynamic_output(dyntools, outfile):
    point_count = 12_001
    large_data = {
        "time": list(range(point_count)),
        1: list(range(point_count)),
        2: list(range(point_count)),
    }

    class LargeCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "LARGE RUN", dict(CHANNELS), large_data

    dyntools.CHNF = LargeCHNF

    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "success", result
    assert result["total_points"] == point_count
    assert result["num_points"] == 10_000
    assert result["downsampled"] is True
    assert result["max_points"] == 10_000
    assert result["data"]["time"][0] == 0
    assert result["data"]["time"][-1] == point_count - 1
    assert len(result["data"]["1"]) == 10_000
    assert len(result["data"]["2"]) == 10_000


@pytest.mark.parametrize("max_points", [0, 1, True, 1.5, "10"])
def test_invalid_dynamic_output_point_caps_are_rejected_before_engine_start(
    dyntools, outfile, max_points
):
    result = psse_mcp.read_dynamic_output(
        str(outfile), max_points=max_points
    )

    assert result["status"] == "error"
    assert "max_points must be an integer of at least 2" in result["message"]
    assert dyntools.engine_starts == 0


def test_reading_an_unknown_channel_names_it(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=[1, 99])

    assert result["status"] == "error"
    assert "[99]" in result["message"]


@pytest.mark.parametrize("channels", [[], [0], [-1], [True]])
def test_malformed_channel_selections_are_refused_before_engine_start(
    dyntools, outfile, channels
):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=channels)

    assert result["status"] == "error"
    assert dyntools.engine_starts == 0


@pytest.mark.parametrize(
    "tool", [psse_mcp.list_dynamic_output_channels, psse_mcp.read_dynamic_output]
)
def test_a_missing_output_file_is_reported_before_engine_start(
    dyntools, outfile, tool
):
    result = tool(str(outfile.with_name("missing.out")))

    assert result["status"] == "error"
    assert "does not exist" in result["message"]
    assert dyntools.engine_starts == 0


@pytest.mark.parametrize(
    "tool", [psse_mcp.list_dynamic_output_channels, psse_mcp.read_dynamic_output]
)
def test_an_output_file_outside_the_roots_is_refused(
    dyntools, tmp_path, monkeypatch, tool
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.out"
    outside.write_bytes(b"")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = tool(str(outside))

    assert result["status"] == "error"
    assert "outside allowed MCP roots" in result["message"]
    assert dyntools.engine_starts == 0
