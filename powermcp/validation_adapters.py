"""Adapters that normalize solved pandapower and PyPSA AC power-flow results.

These functions do not run solvers or infer base-MVA/unit conversions. Callers
must solve both networks first and provide a common study base and snapshot.
Stable bus/branch names are preferred; indices are used only when names are empty.
"""
from __future__ import annotations

import math
from typing import Any

from .validation import ResultSnapshot


def _element_id(name: Any, fallback: Any) -> str:
    if name is None:
        return str(fallback)
    text = str(name).strip()
    return text if text else str(fallback)


def _table_element_id(table: Any, index: Any) -> str:
    name = table.at[index, "name"] if "name" in table.columns else None
    return _element_id(name, index)


def snapshot_from_pandapower(
    net: Any,
    *,
    case_id: str,
    study_type: str = "ac_power_flow",
) -> ResultSnapshot:
    """Build a snapshot from a solved pandapower network (angles in degrees)."""
    values: dict[str, float] = {}
    bus_table = net.bus
    for index, row in net.res_bus.iterrows():
        name = _element_id(bus_table.at[index, "name"], index)
        values[f"bus:{name}:vm_pu"] = float(row["vm_pu"])
        values[f"bus:{name}:va_deg"] = float(row["va_degree"])

    if hasattr(net, "res_line") and hasattr(net, "line"):
        for index, row in net.res_line.iterrows():
            name = _element_id(net.line.at[index, "name"], index)
            values[f"branch:{name}:p_from_mw"] = float(row["p_from_mw"])
            values[f"branch:{name}:p_to_mw"] = float(row["p_to_mw"])

    return ResultSnapshot(
        engine="pandapower",
        case_id=case_id,
        study_type=study_type,
        base_mva=float(net.sn_mva),
        converged=bool(net.get("converged", False)),
        values=values,
    )


def snapshot_from_pypsa(
    network: Any,
    *,
    case_id: str,
    base_mva: float,
    converged: bool,
    snapshot: Any = None,
    study_type: str = "ac_power_flow",
    angle_unit: str = "rad",
) -> ResultSnapshot:
    """Build a snapshot from solved PyPSA results.

    PyPSA bus voltage angles are normally radians; pass angle_unit="deg"
    only if the supplied result table has already been converted to degrees.
    base_mva and converged are explicit because PyPSA networks do not expose a
    universally equivalent pandapower sn_mva/converged pair.
    """
    if angle_unit not in {"rad", "deg"}:
        raise ValueError("angle_unit must be 'rad' or 'deg'")
    if snapshot is None:
        snapshots = network.snapshots
        if len(snapshots) != 1:
            raise ValueError("snapshot must be specified unless there is exactly one snapshot")
        snapshot = snapshots[0]

    values: dict[str, float] = {}
    vm = network.buses_t.v_mag_pu.loc[snapshot]
    va = network.buses_t.v_ang.loc[snapshot]
    for bus_id in network.buses.index:
        name = _table_element_id(network.buses, bus_id)
        values[f"bus:{name}:vm_pu"] = float(vm[bus_id])
        angle = float(va[bus_id])
        if angle_unit == "rad":
            angle = math.degrees(angle)
        values[f"bus:{name}:va_deg"] = angle

    if hasattr(network, "lines_t") and hasattr(network.lines_t, "p0"):
        p0 = network.lines_t.p0.loc[snapshot]
        p1 = network.lines_t.p1.loc[snapshot]
        for line_id in network.lines.index:
            name = _table_element_id(network.lines, line_id)
            values[f"branch:{name}:p_from_mw"] = float(p0[line_id])
            values[f"branch:{name}:p_to_mw"] = float(p1[line_id])

    return ResultSnapshot(
        engine="pypsa",
        case_id=case_id,
        study_type=study_type,
        base_mva=float(base_mva),
        converged=bool(converged),
        values=values,
    )
