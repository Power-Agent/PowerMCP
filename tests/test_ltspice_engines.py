"""The LTSpice server starts without matplotlib or spicelib installed.

Neither package is needed to create a netlist, run LTspice or read a log, and
the two tools that do need one say which one to install.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys

import pytest

from powermcp.registry import get_tool

_ENTRY = get_tool("ltspice").resolve_entry_script()


@pytest.fixture()
def ltspice(monkeypatch):
    """The server module, imported with both engines unimportable.

    Binding a module name to None in sys.modules makes `import name` raise
    ImportError, which is what a machine without the package does.
    """
    for name in ("matplotlib", "matplotlib.pyplot", "spicelib", "spicelib.raw",
                 "spicelib.raw.raw_read"):
        monkeypatch.setitem(sys.modules, name, None)

    spec = importlib.util.spec_from_file_location("ltspice_mcp_under_test", str(_ENTRY))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "ltspice_mcp_under_test", module)
    spec.loader.exec_module(module)
    return module


def test_the_server_registers_its_tools_without_either_engine(ltspice):
    names = {tool.name for tool in asyncio.run(ltspice.mcp.list_tools())}
    assert "create_simulation_session" in names
    assert "plot_specific_traces" in names
    assert "list_available_traces" in names


def test_a_session_can_still_be_created_without_either_engine(ltspice, tmp_path, monkeypatch):
    monkeypatch.setattr(ltspice, "_output_dir", lambda: str(tmp_path / "runs"))

    result = asyncio.run(ltspice.create_simulation_session("* title\n.end\n"))
    assert result["status"] == "success"
    assert result["netlist_content"] == "* title\n.end\n"


def test_reading_traces_without_spicelib_says_what_to_install(ltspice, tmp_path):
    raw = tmp_path / "circuit.raw"
    raw.write_bytes(b"")

    result = asyncio.run(ltspice.list_available_traces(str(raw)))
    assert result["status"] == "error"
    assert "PyLTSpice" in result["message"]


def test_plotting_without_spicelib_says_what_to_install(ltspice, tmp_path):
    raw = tmp_path / "circuit.raw"
    raw.write_bytes(b"")

    result = asyncio.run(ltspice.plot_specific_traces(str(raw), str(tmp_path), ["V(out)"]))
    assert result["status"] == "error"
    assert "PyLTSpice" in result["message"]


def test_plotting_without_matplotlib_says_what_to_install(ltspice, tmp_path, monkeypatch):
    """With spicelib present, the missing matplotlib is the one named."""
    monkeypatch.setattr(ltspice, "_raw_reader", lambda: object)
    raw = tmp_path / "circuit.raw"
    raw.write_bytes(b"")

    result = asyncio.run(ltspice.plot_specific_traces(str(raw), str(tmp_path), ["V(out)"]))
    assert result["status"] == "error"
    assert "matplotlib" in result["message"]


def test_a_refused_path_is_reported_before_either_engine_is_wanted(ltspice, tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "circuit.raw").write_bytes(b"")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = asyncio.run(ltspice.list_available_traces(str(outside / "circuit.raw")))
    assert result["status"] == "error"
    assert "raw_file_path" in result["message"]
