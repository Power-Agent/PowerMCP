from __future__ import annotations

import pandapower as pp

from powermcp.audit import audit_network


def test_audit_clean_network():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110, min_vm_pu=0.95, max_vm_pu=1.05)
    report = audit_network(net)
    assert report.status == "ok"
    assert report.counts == {"errors": 0, "warnings": 0, "info": 0}


def test_audit_flags_reversed_voltage_limits():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110, min_vm_pu=1.10, max_vm_pu=1.00)
    report = audit_network(net)
    assert report.status == "error"
    assert any(f.code == "BUS_VOLTAGE_RANGE_REVERSED" for f in report.findings)


def test_audit_flags_invalid_line():
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=110)
    b1 = pp.create_bus(net, vn_kv=110)
    pp.create_line_from_parameters(
        net,
        b0,
        b1,
        length_km=0,
        r_ohm_per_km=0,
        x_ohm_per_km=0,
        c_nf_per_km=0,
        max_i_ka=0,
    )
    report = audit_network(net)
    assert report.status == "error"
    codes = {f.code for f in report.findings}
    assert "LINE_NONPOSITIVE_LENGTH" in codes
    assert "LINE_ZERO_IMPEDANCE" in codes
    assert "LINE_MISSING_RATING" in codes


def test_audit_does_not_run_power_flow():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110)
    original = net.converged
    report = audit_network(net)
    assert net.converged == original
    assert report.status == "ok"
