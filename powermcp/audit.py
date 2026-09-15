"""Deterministic, solver-independent network audit helpers.

The audit layer is intentionally separate from the MCP server wrappers. It turns
common pre-solve checks into a stable JSON-serializable report that an agent can
inspect before invoking a solver.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    code: str
    message: str
    element: str | None = None
    index: int | None = None


@dataclass(frozen=True)
class AuditReport:
    status: str
    counts: dict[str, int]
    findings: list[AuditFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "counts": dict(self.counts),
            "findings": [asdict(f) for f in self.findings],
        }


def audit_network(net: Any) -> AuditReport:
    """Audit a pandapower network without running a power flow.

    Checks are conservative and structural: bus voltage limits, inactive buses,
    missing/invalid line and transformer ratings, invalid impedance values,
    and disconnected buses. The function does not mutate the network.
    """
    findings: list[AuditFinding] = []

    def add(severity: str, code: str, message: str, element: str | None = None,
            index: int | None = None) -> None:
        findings.append(AuditFinding(severity, code, message, element, index))

    buses = getattr(net, "bus", None)
    if buses is not None:
        for idx, row in buses.iterrows():
            if not bool(row.get("in_service", True)):
                add("warning", "BUS_OUT_OF_SERVICE", "Bus is out of service.", "bus", int(idx))
            for col, lo, hi, code in (
                ("min_vm_pu", 0.0, 1.1, "BUS_MIN_VM_INVALID"),
                ("max_vm_pu", 0.9, 2.0, "BUS_MAX_VM_INVALID"),
            ):
                if col in row and row[col] is not None:
                    value = float(row[col])
                    if not (lo <= value <= hi):
                        add("error", code, f"{col}={value} is outside a valid range.", "bus", int(idx))
            if "min_vm_pu" in row and "max_vm_pu" in row:
                if float(row["min_vm_pu"]) > float(row["max_vm_pu"]):
                    add("error", "BUS_VOLTAGE_RANGE_REVERSED",
                        "min_vm_pu is greater than max_vm_pu.", "bus", int(idx))

    lines = getattr(net, "line", None)
    if lines is not None:
        for idx, row in lines.iterrows():
            length = row.get("length_km")
            r = row.get("r_ohm_per_km")
            x = row.get("x_ohm_per_km")
            if length is not None and float(length) <= 0:
                add("error", "LINE_NONPOSITIVE_LENGTH", "Line length must be positive.", "line", int(idx))
            if r is not None and float(r) < 0:
                add("error", "LINE_NEGATIVE_RESISTANCE", "Line resistance cannot be negative.", "line", int(idx))
            if x is not None and float(x) == 0 and r is not None and float(r) == 0:
                add("error", "LINE_ZERO_IMPEDANCE", "Line has zero series impedance.", "line", int(idx))
            if "max_i_ka" in row and float(row["max_i_ka"]) <= 0:
                add("warning", "LINE_MISSING_RATING", "Line current rating is not positive.", "line", int(idx))

    trafos = getattr(net, "trafo", None)
    if trafos is not None:
        for idx, row in trafos.iterrows():
            if "sn_mva" in row and float(row["sn_mva"]) <= 0:
                add("warning", "TRAFO_MISSING_RATING", "Transformer apparent-power rating is not positive.", "trafo", int(idx))
            if "vk_percent" in row and float(row["vk_percent"]) <= 0:
                add("error", "TRAFO_INVALID_SHORT_CIRCUIT", "Transformer vk_percent must be positive.", "trafo", int(idx))

    # Use pandapower's graph utilities when available; avoid running a PF.
    try:
        import pandapower.topology as top
        import networkx as nx

        graph = top.create_nxgraph(net, nogobuses=net.bus.index[~net.bus.in_service] if hasattr(net.bus, "in_service") else None)
        connected = set().union(*(set(c) for c in nx.connected_components(graph))) if graph.number_of_nodes() else set()
        in_service_buses = set(net.bus.index[net.bus.in_service]) if "in_service" in net.bus else set(net.bus.index)
        disconnected = sorted(in_service_buses - connected)
        for idx in disconnected:
            add("error", "DISCONNECTED_BUS", "In-service bus is disconnected from the network graph.", "bus", int(idx))
    except Exception:
        # Structural checks should never make the audit itself fail.
        pass

    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    infos = sum(f.severity == "info" for f in findings)
    status = "error" if errors else "warning" if warnings else "ok"
    return AuditReport(
        status=status,
        counts={"errors": errors, "warnings": warnings, "info": infos},
        findings=findings,
    )
