import copy
import importlib.util
import json
from pathlib import Path
import sys

import pandapower as pp
import pandapower.networks as pn
import pytest

# The validator ships inside the force-included pandapower/ server directory,
# so load it by path, as the server's own directory is not a package.
_OP_PATH = Path(__file__).resolve().parents[1] / "pandapower" / "operating_point.py"
_SPEC = importlib.util.spec_from_file_location("powermcp_pandapower_operating_point", _OP_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_OP_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _OP_MODULE
_SPEC.loader.exec_module(_OP_MODULE)
validate_operating_point = _OP_MODULE.validate_operating_point

_SERVER_PATH = _OP_PATH.parent / "panda_mcp.py"


def _load_server_like_runner():
    # The runner puts only the server's own directory on sys.path.
    server_dir = str(_SERVER_PATH.parent)
    sys.path.insert(0, server_dir)
    try:
        spec = importlib.util.spec_from_file_location("powermcp_pandapower_server_op", _SERVER_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(server_dir)


def test_case9_clean_operating_point_is_ok():
    net = pn.case9()
    pp.runpp(net)
    report = validate_operating_point(net)
    assert report["status"] == "ok"
    assert report["converged"] is True
    assert report["summary"]["min_vm_pu"] >= 0.95
    assert report["violations"] == []


def test_voltage_violation_is_reported():
    net = pn.case9()
    pp.runpp(net)
    net.res_bus.loc[0, "vm_pu"] = 0.90
    report = validate_operating_point(net)
    assert report["status"] == "error"
    assert report["violations"][0]["code"] == "BUS_UNDERVOLTAGE"
    assert report["violations"][0]["index"] == 0


def test_line_overload_is_reported():
    net = pn.case9()
    pp.runpp(net)
    net.res_line.loc[0, "loading_percent"] = 125.0
    report = validate_operating_point(net)
    assert report["status"] == "error"
    assert any(v["code"] == "LINE_OVERLOAD" for v in report["violations"])


def test_near_limit_is_warning_without_violation():
    net = pn.case9()
    pp.runpp(net)
    net.res_bus.loc[0, "vm_pu"] = 0.953
    report = validate_operating_point(net)
    assert report["status"] == "warning"
    assert report["violations"] == []
    assert "BUS_VOLTAGE_NEAR_LIMIT" in report["near_limit_codes"]


def test_not_converged_is_failed():
    net = pn.case9()
    report = validate_operating_point(net)
    assert report["status"] == "failed"
    assert "converged" in report["message"]


@pytest.mark.parametrize(
    ("criteria", "message"),
    [
        ({"voltage_min_pu": 1.1, "voltage_max_pu": 1.0}, "Require 0 <="),
        ({"line_loading_limit_percent": float("nan")}, "finite"),
        ({"trafo_loading_limit_percent": -5}, "positive"),
    ],
)
def test_invalid_criteria_is_failed(criteria, message):
    net = pn.case9()
    pp.runpp(net)
    report = validate_operating_point(net, **criteria)
    assert report["status"] == "failed"
    assert message in report["message"]
    json.dumps(report, allow_nan=False)


def test_validation_does_not_mutate_network():
    net = pn.case9()
    pp.runpp(net)
    before = copy.deepcopy(net.res_bus)
    validate_operating_point(net)
    assert net.res_bus.equals(before)


def test_overvoltage_is_reported_with_machine_readable_fields():
    net = pn.example_simple()
    net.ext_grid["vm_pu"] = 1.10
    pp.runpp(net)
    report = validate_operating_point(net)
    assert report["status"] == "error"
    finding = next(v for v in report["violations"] if v["code"] == "BUS_OVERVOLTAGE")
    assert finding == {
        "severity": "error",
        "code": "BUS_OVERVOLTAGE",
        "element": "bus",
        "index": finding["index"],
        "metric": "vm_pu",
        "value": float(net.res_bus.at[finding["index"], "vm_pu"]),
        "limit": 1.05,
    }


def test_trafo_overload_and_near_limit_are_reported():
    net = pn.example_simple()
    net.trafo["sn_mva"] = 1.0
    pp.runpp(net)
    report = validate_operating_point(net)
    assert report["status"] == "error"
    finding = next(v for v in report["violations"] if v["code"] == "TRAFO_OVERLOAD")
    assert finding["metric"] == "loading_percent"
    assert finding["limit"] == 100.0
    assert report["summary"]["max_trafo_loading_percent"] == net.res_trafo["loading_percent"].max()

    net = pn.example_simple()
    pp.runpp(net)
    net.res_trafo["loading_percent"] = 98.0
    report = validate_operating_point(net)
    assert report["status"] == "warning"
    assert "TRAFO_LOADING_NEAR_LIMIT" in report["near_limit_codes"]


def test_three_winding_transformer_is_checked():
    net = pn.example_multivoltage()
    pp.runpp(net)
    report = validate_operating_point(net, trafo_loading_limit_percent=20)
    assert any(
        v["code"] == "TRAFO3W_OVERLOAD" and v["element"] == "trafo3w"
        for v in report["violations"]
    )
    expected_loss = sum(net[t]["pl_mw"].sum() for t in ("res_line", "res_trafo", "res_trafo3w"))
    assert report["summary"]["p_loss_mw"] == pytest.approx(expected_loss)

    net.res_trafo3w["loading_percent"] = 150.0
    report = validate_operating_point(net)
    assert report["summary"]["max_trafo_loading_percent"] == 150.0


def test_out_of_service_bus_is_skipped():
    net = pn.case9()
    net.bus.loc[8, "in_service"] = False
    pp.runpp(net)
    report = validate_operating_point(net)
    assert not any(v["code"] == "NONFINITE_BUS_VOLTAGE" for v in report["violations"])
    assert report["status"] != "error"


def test_isolated_bus_result_serializes_as_strict_json():
    net = pn.case9()
    bus = pp.create_bus(net, vn_kv=345.0)
    pp.create_load(net, bus, p_mw=10.0)
    pp.runpp(net)
    report = validate_operating_point(net)
    json.dumps(report, allow_nan=False)
    finding = next(v for v in report["violations"] if v["code"] == "NONFINITE_BUS_VOLTAGE")
    assert finding["index"] == bus
    assert finding["value"] is None
    assert report["status"] == "error"


def test_violating_element_is_not_also_near_limit():
    net = pn.case9()
    pp.runpp(net)
    report = validate_operating_point(net, line_loading_limit_percent=60)
    assert report["status"] == "error"
    assert report["near_limit_codes"] == []
    assert report["counts"]["warnings"] == 0

    net.res_line.loc[0, "loading_percent"] = 58.5
    report = validate_operating_point(net, line_loading_limit_percent=60)
    assert report["near_limit_codes"] == ["LINE_LOADING_NEAR_LIMIT"]


def test_server_reports_error_when_no_network_is_loaded():
    server = _load_server_like_runner()
    server._current_net = None
    result = server.validate_operating_point()
    assert result["status"] == "error"
    assert "No pandapower network" in result["message"]
    assert "validation_status" not in result


def test_server_reports_error_when_validation_cannot_run():
    # A network with no converged power flow cannot be validated; that is a
    # could-not-run outcome, so it must not surface as a verdict.
    server = _load_server_like_runner()
    server._current_net = pn.case9()
    result = server.validate_operating_point()
    assert result["status"] == "error"
    assert result["message"] == "No converged power-flow result is available."
    assert "validation_status" not in result


def test_server_success_carries_verdict_and_passes_limits_through():
    server = _load_server_like_runner()
    net = pn.case9()
    pp.runpp(net)
    server._current_net = net

    clean = server.validate_operating_point()
    assert clean["status"] == "success"
    assert clean["validation_status"] == "ok"
    assert clean["counts"]["errors"] == 0

    # A tight band turns the same converged network into a violation report,
    # proving the limits reach the validator rather than defaults.
    tight = server.validate_operating_point(voltage_min_pu=1.05, voltage_max_pu=1.06)
    assert tight["status"] == "success"
    assert tight["validation_status"] == "error"
    assert tight["criteria"]["voltage_min_pu"] == 1.05
    assert any(v["code"] == "BUS_UNDERVOLTAGE" for v in tight["violations"])


def test_server_registers_tool_and_documents_the_envelope():
    server = _load_server_like_runner()
    assert "validate_operating_point" in server.mcp._tool_manager._tools
    doc = server.validate_operating_point.__doc__
    assert "run_power_flow" in doc
    for word in ("success", "error", "validation_status", "ok", "warning"):
        assert f"``{word}``" in doc
