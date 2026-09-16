"""The OpenDSS server starts without a working OpenDSS engine.

Building the py_dss_interface DSS object loads the OpenDSS engine library. Doing
that at import took down the whole server, including its tool listing, on any
machine where the library is missing or refuses to load. The engine is built on
the first tool call instead, and a failure there is reported as a result.
"""

from __future__ import annotations

import sys
import types

import pytest

from powermcp.registry import get_tool

OPENDSS_DIR = str(get_tool("opendss").resolve_server_dir())


class _RefusingDSS:
    def __init__(self) -> None:
        raise OSError("libopendssc.so: cannot open shared object file")


def _fake_toolkit() -> types.SimpleNamespace:
    """py_dss_toolkit's dss_tools, with the calls the configuration tools make."""
    return types.SimpleNamespace(
        configuration=types.SimpleNamespace(
            compile_dss=lambda path: None,
            circuit_readiness=lambda: {"ready": True},
        ),
        update_dss=lambda _dss: None,
    )


_SERVER_PACKAGES = ("core", "utils", "opendss_tools")


def _drop_server_modules() -> None:
    """Forget the server's own modules so the next import rebinds the fakes."""
    for name in list(sys.modules):
        root = name.split(".", 1)[0]
        if root in _SERVER_PACKAGES:
            del sys.modules[name]


@pytest.fixture()
def opendss(monkeypatch):
    """The server's configuration tools, built on a DSS that refuses to load.

    The server's packages are named `core`, `utils` and `opendss_tools`, which
    are generic enough to collide with anything else on sys.path, so both the
    path entry and the imported modules are withdrawn afterwards.
    """
    interface = types.ModuleType("py_dss_interface")
    interface.DSS = _RefusingDSS
    toolkit = types.ModuleType("py_dss_toolkit")
    toolkit.dss_tools = _fake_toolkit()
    monkeypatch.setitem(sys.modules, "py_dss_interface", interface)
    monkeypatch.setitem(sys.modules, "py_dss_toolkit", toolkit)

    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    sys.path.insert(0, OPENDSS_DIR)
    _drop_server_modules()
    try:
        from core.server import create_mcp
        import core.engine as engine
        import opendss_tools.configuration as configuration

        engine._dss = None
        yield types.SimpleNamespace(
            create_mcp=create_mcp, configuration=configuration, engine=engine
        )
    finally:
        _drop_server_modules()
        sys.modules.update(
            {k: v for k, v in saved_modules.items() if k.split(".", 1)[0] in _SERVER_PACKAGES}
        )
        sys.path[:] = saved_path


def test_the_server_builds_its_tools_without_a_working_engine(opendss):
    """Building the server must not touch the engine."""
    server = opendss.create_mcp()
    assert server is not None


def test_an_engine_that_refuses_to_load_is_reported_as_a_result(opendss, tmp_path):
    case = tmp_path / "case.dss"
    case.write_text("New Circuit.test\n")

    result = opendss.configuration.compile_opendss_file(str(case))
    assert result["status"] == "error"
    assert "libopendssc.so" in result["message"]


def test_a_path_outside_the_allowed_roots_is_refused(opendss, tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    case = outside / "case.dss"
    case.write_text("New Circuit.test\n")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = opendss.configuration.compile_opendss_file(str(case))
    assert result["status"] == "error"
    assert "dss_file" in result["message"]


def test_a_compile_that_works_reports_the_success_shape(opendss, tmp_path):
    """With a DSS instance that builds, the tool reports through payload."""
    opendss.engine._dss = object()
    case = tmp_path / "case.dss"
    case.write_text("New Circuit.test\n")

    result = opendss.configuration.compile_opendss_file(str(case))
    assert result["status"] == "success"
    assert result["payload"]["circuit_loaded"] is True
    assert result["payload"]["circuit_readiness"] == {"ready": True}
