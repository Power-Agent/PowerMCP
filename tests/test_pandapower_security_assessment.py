"""Tests for topology-aware pandapower N-1 security assessment."""
from pathlib import Path
import sys

import pandapower as pp
import pandapower.networks as pn

_SERVER_DIR = str(Path(__file__).resolve().parents[1] / "pandapower")
sys.path.insert(0, _SERVER_DIR)
try:
    from security_assessment import _evaluate_results, run_security_assessment
finally:
    sys.path.remove(_SERVER_DIR)


def test_case14_assessment_is_deterministic_and_does_not_mutate_input():
    net = pn.case14()
    before = net.line.in_service.copy(), net.trafo.in_service.copy()

    first = run_security_assessment(net)
    second = run_security_assessment(net)

    assert first["status"] == "success"
    assert first["analysis_type"] == "N-1"
    assert first["contingency_count"] == len(net.line) + len(net.trafo)
    assert first["results"] == second["results"]
    assert (net.line.in_service == before[0]).all()
    assert (net.trafo.in_service == before[1]).all()
    assert set(first["summary"]) == {
        "secure", "limit_violations", "islanding", "nonconvergent", "errors"
    }


def test_line_outage_reports_unsupplied_load_instead_of_generic_solver_error():
    net = pp.create_empty_network()
    source = pp.create_bus(net, vn_kv=110)
    remote = pp.create_bus(net, vn_kv=110)
    pp.create_ext_grid(net, bus=source)
    line = pp.create_line_from_parameters(
        net, from_bus=source, to_bus=remote, length_km=1,
        r_ohm_per_km=0.1, x_ohm_per_km=0.1,
        c_nf_per_km=0, max_i_ka=1,
    )
    pp.create_load(net, bus=remote, p_mw=12.5, q_mvar=2.0)
    # Positive sgen power is generation, not additional unserved demand.
    pp.create_sgen(net, bus=remote, p_mw=7.5, q_mvar=0.0)

    report = run_security_assessment(net, elements=["line"])

    assert report["contingency_count"] == 1
    result = report["results"][0]
    assert result["contingency"] == f"line_{line}"
    assert result["classification"] == "islanding"
    assert result["converged"] is False
    assert result["violations"]["severity"]["unserved_load_mw"] == 12.5
    assert result["unsupplied_islands"][0]["buses"] == [remote]
    assert bool(net.line.at[line, "in_service"])


def test_element_specific_line_loading_limit_overrides_fallback():
    net = pn.case14()
    line = net.line.index[0]
    net.line.at[line, "max_loading_percent"] = 1.0
    pp.runpp(net)

    violations = _evaluate_results(
        net,
        voltage_min_pu=0.95,
        voltage_max_pu=1.05,
        line_loading_limit_percent=1000.0,
        trafo_loading_limit_percent=1000.0,
    )

    assert any(item["index"] == line for item in violations["line_overloads"])
    assert all(
        item["limit_percent"] == 1.0
        for item in violations["line_overloads"]
        if item["index"] == line
    )


def test_invalid_voltage_limits_are_rejected():
    net = pn.case14()
    try:
        run_security_assessment(net, voltage_min_pu=1.05, voltage_max_pu=0.95)
    except ValueError as exc:
        assert "Voltage limits" in str(exc)
    else:
        raise AssertionError("Invalid voltage limits were accepted")
