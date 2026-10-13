"""Integration test: compare independently solved two-bus AC power flows."""
from __future__ import annotations

import pytest

from powermcp.validation import MetricTolerance, compare_snapshots
from powermcp.validation_adapters import snapshot_from_pandapower, snapshot_from_pypsa



class _FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.columns = sorted({key for row in rows.values() for key in row})
        self.at = self

    def __getitem__(self, key):
        index, column = key
        return self.rows[index].get(column)

    def iterrows(self):
        return iter(self.rows.items())


class _FakeNetwork:
    def __init__(self, names):
        self.bus = _FakeTable({i: {"name": name} for i, name in enumerate(names)})
        self.res_bus = _FakeTable({
            i: {"vm_pu": 1.0 - i * 0.001, "va_degree": float(i)}
            for i in range(len(names))
        })
        self.sn_mva = 100.0

    def get(self, key, default=None):
        return getattr(self, key, default)


def test_pandapower_adapter_falls_back_to_index_for_nan_names():
    net = _FakeNetwork(["Station", float("nan"), float("nan"), None])
    snapshot = snapshot_from_pandapower(net, case_id="unnamed-buses")

    assert "bus:Station:vm_pu" in snapshot.values
    assert "bus:1:vm_pu" in snapshot.values
    assert "bus:2:vm_pu" in snapshot.values
    assert "bus:3:vm_pu" in snapshot.values
    assert len(snapshot.values) == 8


def test_pandapower_adapter_rejects_duplicate_element_names():
    net = _FakeNetwork(["Station", "Station"])
    with pytest.raises(ValueError, match="duplicate normalized metric key"):
        snapshot_from_pandapower(net, case_id="duplicate-buses")

def test_pandapower_and_pypsa_two_bus_ac_power_flow_agree():
    pp = pytest.importorskip("pandapower")
    pypsa = pytest.importorskip("pypsa")

    # Identical two-bus system: 110-kV buses, one 0.1+j0.4-ohm line,
    # a 50-MW/10-Mvar load, and a 1.0-pu slack bus. Stable IDs are shared.
    net = pp.create_empty_network(sn_mva=100.0)
    pp_b0 = pp.create_bus(net, vn_kv=110.0, name="B0")
    pp_b1 = pp.create_bus(net, vn_kv=110.0, name="B1")
    pp.create_ext_grid(net, pp_b0, vm_pu=1.0, va_degree=0.0)
    pp.create_line_from_parameters(
        net, pp_b0, pp_b1, length_km=1.0,
        r_ohm_per_km=0.1, x_ohm_per_km=0.4, c_nf_per_km=0.0,
        max_i_ka=1.0, name="L0",
    )
    pp.create_load(net, pp_b1, p_mw=50.0, q_mvar=10.0)
    pp.runpp(net, calculate_voltage_angles=True)
    left = snapshot_from_pandapower(net, case_id="two-bus")

    network = pypsa.Network()
    network.add("Bus", "B0", v_nom=110.0)
    network.add("Bus", "B1", v_nom=110.0)
    network.add("Line", "L0", bus0="B0", bus1="B1", r=0.1, x=0.4, b=0.0, s_nom=100.0)
    network.add("Load", "load", bus="B1", p_set=50.0, q_set=10.0)
    network.add("Generator", "slack", bus="B0", control="Slack", p_set=0.0, vm_pu=1.0)
    pf_result = network.pf()
    converged_frame = pf_result.get("converged")
    converged = bool(converged_frame.iloc[0].all()) if converged_frame is not None else False
    right = snapshot_from_pypsa(network, case_id="two-bus", base_mva=100.0, converged=converged)

    assert left.converged and right.converged
    report = compare_snapshots(
        left,
        right,
        default_tolerance=MetricTolerance(atol=2e-3, rtol=2e-3),
    )
    assert report.compared >= 6
    assert report.passed, report
