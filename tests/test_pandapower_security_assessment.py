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



def _three_bus_mesh():
    net = pp.create_empty_network()
    buses = [pp.create_bus(net, vn_kv=110) for _ in range(3)]
    pp.create_ext_grid(net, bus=buses[0])
    lines = [
        pp.create_line_from_parameters(
            net, from_bus=buses[a], to_bus=buses[b], length_km=1,
            r_ohm_per_km=0.1, x_ohm_per_km=0.1,
            c_nf_per_km=0, max_i_ka=1,
        )
        for a, b in ((0, 1), (1, 2), (0, 2))
    ]
    pp.create_load(net, bus=buses[2], p_mw=8.0, q_mvar=1.0)
    return net, lines, buses


def test_n2_assessment_evaluates_simultaneous_pairs_deterministically():
    from security_assessment import run_n2_security_assessment

    net, lines, _ = _three_bus_mesh()
    before = net.line.in_service.copy()

    first = run_n2_security_assessment(net, elements=["line"])
    second = run_n2_security_assessment(net, elements=["line"])

    assert first["status"] == "success"
    assert first["analysis_type"] == "N-2"
    assert first["contingency_count"] == 3
    assert first["results"] == second["results"]
    assert all(len(result["elements"]) == 2 for result in first["results"])
    assert {
        tuple(item["index"] for item in result["elements"])
        for result in first["results"]
    } == {(lines[0], lines[1]), (lines[0], lines[2]), (lines[1], lines[2])}
    assert (net.line.in_service == before).all()


def test_n2_assessment_reports_load_islanded_by_two_simultaneous_outages():
    from security_assessment import run_n2_security_assessment

    net = pp.create_empty_network()
    source, middle, remote = [
        pp.create_bus(net, vn_kv=110) for _ in range(3)
    ]
    pp.create_ext_grid(net, bus=source)
    first = pp.create_line_from_parameters(
        net, from_bus=source, to_bus=middle, length_km=1,
        r_ohm_per_km=0.1, x_ohm_per_km=0.1,
        c_nf_per_km=0, max_i_ka=1,
    )
    second = pp.create_line_from_parameters(
        net, from_bus=middle, to_bus=remote, length_km=1,
        r_ohm_per_km=0.1, x_ohm_per_km=0.1,
        c_nf_per_km=0, max_i_ka=1,
    )
    pp.create_load(net, bus=remote, p_mw=8.0, q_mvar=1.0)

    report = run_n2_security_assessment(net, elements=["line"])

    assert report["contingency_count"] == 1
    result = report["results"][0]
    assert result["elements"] == [
        {"element": "line", "index": first},
        {"element": "line", "index": second},
    ]
    assert result["classification"] == "islanding"
    assert result["violations"]["severity"]["unserved_load_mw"] == 8.0


def test_n2_candidate_limit_rejects_before_running_contingencies():
    from security_assessment import run_n2_security_assessment

    net, _, _ = _three_bus_mesh()
    try:
        run_n2_security_assessment(
            net, elements=["line"], max_contingencies=2
        )
    except ValueError as exc:
        assert "3 outage pairs" in str(exc)
        assert "max_contingencies=2" in str(exc)
    else:
        raise AssertionError("N-2 candidate limit was not enforced")


def test_n2_requires_at_least_two_active_elements():
    from security_assessment import run_n2_security_assessment

    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110)
    pp.create_ext_grid(net, bus=bus)
    try:
        run_n2_security_assessment(net, elements=["line"])
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("N-2 accepted fewer than two candidate elements")
