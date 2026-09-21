from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys

import pandapower as pp

_AUDIT_PATH = Path(__file__).resolve().parents[1] / "pandapower" / "audit.py"
_SPEC = importlib.util.spec_from_file_location("powermcp_pandapower_audit", _AUDIT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_AUDIT_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _AUDIT_MODULE
_SPEC.loader.exec_module(_AUDIT_MODULE)
audit_network = _AUDIT_MODULE.audit_network


def test_audit_clean_network():
    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110, min_vm_pu=0.95, max_vm_pu=1.05)
    pp.create_ext_grid(net, bus)
    report = audit_network(net)
    assert report.status == "ok"
    assert report.counts == {"errors": 0, "warnings": 0, "info": 0}


def test_audit_flags_reversed_voltage_limits():
    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110, min_vm_pu=1.10, max_vm_pu=1.00)
    pp.create_ext_grid(net, bus)
    report = audit_network(net)
    assert report.status == "error"
    assert any(f.code == "BUS_VOLTAGE_RANGE_REVERSED" for f in report.findings)


def test_audit_flags_nonfinite_voltage_limit():
    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110, min_vm_pu=0.95, max_vm_pu=1.05)
    net.bus.at[bus, "min_vm_pu"] = float("nan")
    pp.create_ext_grid(net, bus)
    report = audit_network(net)
    assert report.status == "error"
    assert any(f.code == "BUS_MIN_VM_INVALID" for f in report.findings)


def test_audit_flags_invalid_line():
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=110)
    b1 = pp.create_bus(net, vn_kv=110)
    pp.create_ext_grid(net, b0)
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


def test_audit_flags_islanded_buses_not_reachable_from_source():
    net = pp.create_empty_network()
    b0, b1, b2, b3 = [pp.create_bus(net, vn_kv=110) for _ in range(4)]
    pp.create_line_from_parameters(
        net, b0, b1, length_km=1, r_ohm_per_km=0.1, x_ohm_per_km=0.1,
        c_nf_per_km=0, max_i_ka=1,
    )
    pp.create_line_from_parameters(
        net, b2, b3, length_km=1, r_ohm_per_km=0.1, x_ohm_per_km=0.1,
        c_nf_per_km=0, max_i_ka=1,
    )
    pp.create_ext_grid(net, b0)

    report = audit_network(net)

    disconnected = {
        f.index for f in report.findings if f.code == "DISCONNECTED_BUS"
    }
    assert report.status == "error"
    assert disconnected == {2, 3}


def test_audit_does_not_run_power_flow_or_mutate_network():
    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110)
    pp.create_ext_grid(net, bus)
    before = copy.deepcopy(net)
    original = net.converged
    report = audit_network(net)
    assert net.converged == original
    assert net.bus.equals(before.bus)
    assert report.status == "ok"


def test_audit_report_is_json_serializable_and_stable():
    net = pp.create_empty_network()
    bus = pp.create_bus(net, vn_kv=110, min_vm_pu=1.10, max_vm_pu=1.00)
    pp.create_ext_grid(net, bus)
    first = audit_network(net).to_dict()
    second = audit_network(net).to_dict()
    assert first == second
    assert isinstance(first["findings"], list)
    assert all(set(f) == {"severity", "code", "message", "element", "index"} for f in first["findings"])


def test_server_audit_reports_failed_when_no_network_is_loaded():
    server_path = Path(__file__).resolve().parents[1] / "pandapower" / "panda_mcp.py"
    server_dir = str(server_path.parent)
    sys.path.insert(0, server_dir)
    try:
        spec = importlib.util.spec_from_file_location("powermcp_pandapower_server", server_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        original = module._current_net
        module._current_net = None
        try:
            result = module.audit_network()
        finally:
            module._current_net = original
    finally:
        sys.path.remove(server_dir)

    assert result["status"] == "failed"
    assert "No pandapower network is currently loaded" in result["message"]

# Keep the server-boundary test on the same import path used by the runner.
