import copy

import pandapower as pp
import pandapower.networks as pn

from operating_point import validate_operating_point


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


def test_invalid_criteria_is_failed():
    net = pn.case9()
    report = validate_operating_point(net, voltage_min_pu=1.1, voltage_max_pu=1.0)
    assert report["status"] == "failed"


def test_validation_does_not_mutate_network():
    net = pn.case9()
    pp.runpp(net)
    before = copy.deepcopy(net.res_bus)
    validate_operating_point(net)
    assert net.res_bus.equals(before)
