"""Deterministic, solver-independent pandapower network audit helpers.

The audit layer contains structural pre-flight checks for the pandapower
server. It never runs a power flow and does not mutate the supplied network.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
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
        """Return a stable JSON-serializable representation of the report."""
        return {
            "status": self.status,
            "counts": dict(self.counts),
            "findings": [asdict(finding) for finding in self.findings],
        }


def audit_network(net: Any) -> AuditReport:
    """Audit a pandapower network without running a power flow.

    Checks are deliberately structural: bus service state and voltage limits,
    invalid line parameters and ratings, transformer ratings, and buses that
    are not supplied by any in-service source. The function does not mutate
    ``net`` and does not execute a solver.
    """
    findings: list[AuditFinding] = []

    def add(
        severity: str,
        code: str,
        message: str,
        element: str | None = None,
        index: int | None = None,
    ) -> None:
        findings.append(AuditFinding(severity, code, message, element, index))

    def finite(value: Any) -> bool:
        try:
            return math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    buses = getattr(net, "bus", None)
    if buses is not None:
        for idx, row in buses.iterrows():
            if not bool(row.get("in_service", True)):
                add("warning", "BUS_OUT_OF_SERVICE", "Bus is out of service.", "bus", int(idx))

            minimum = row.get("min_vm_pu")
            maximum = row.get("max_vm_pu")
            if minimum is not None:
                if not finite(minimum) or float(minimum) < 0:
                    add("error", "BUS_MIN_VM_INVALID", "min_vm_pu must be finite and non-negative.", "bus", int(idx))
            if maximum is not None:
                if not finite(maximum) or float(maximum) <= 0:
                    add("error", "BUS_MAX_VM_INVALID", "max_vm_pu must be finite and positive.", "bus", int(idx))
            if (
                minimum is not None
                and maximum is not None
                and finite(minimum)
                and finite(maximum)
                and float(minimum) > float(maximum)
            ):
                add(
                    "error",
                    "BUS_VOLTAGE_RANGE_REVERSED",
                    "min_vm_pu is greater than max_vm_pu.",
                    "bus",
                    int(idx),
                )

    lines = getattr(net, "line", None)
    if lines is not None:
        for idx, row in lines.iterrows():
            length = row.get("length_km")
            resistance = row.get("r_ohm_per_km")
            reactance = row.get("x_ohm_per_km")
            if length is not None and (not finite(length) or float(length) <= 0):
                add("error", "LINE_NONPOSITIVE_LENGTH", "Line length must be positive.", "line", int(idx))
            if resistance is not None and (not finite(resistance) or float(resistance) < 0):
                add(
                    "error",
                    "LINE_NEGATIVE_RESISTANCE",
                    "Line resistance cannot be negative.",
                    "line",
                    int(idx),
                )
            if (
                reactance is not None
                and resistance is not None
                and finite(reactance)
                and finite(resistance)
                and float(reactance) == 0
                and float(resistance) == 0
            ):
                add("error", "LINE_ZERO_IMPEDANCE", "Line has zero series impedance.", "line", int(idx))
            if "max_i_ka" in row and (
                not finite(row["max_i_ka"]) or float(row["max_i_ka"]) <= 0
            ):
                add("warning", "LINE_MISSING_RATING", "Line current rating is not positive.", "line", int(idx))

    trafos = getattr(net, "trafo", None)
    if trafos is not None:
        for idx, row in trafos.iterrows():
            if "sn_mva" in row and (
                not finite(row["sn_mva"]) or float(row["sn_mva"]) <= 0
            ):
                add(
                    "warning",
                    "TRAFO_MISSING_RATING",
                    "Transformer apparent-power rating is not positive.",
                    "trafo",
                    int(idx),
                )
            if "vk_percent" in row and (
                not finite(row["vk_percent"]) or float(row["vk_percent"]) <= 0
            ):
                add(
                    "error",
                    "TRAFO_INVALID_SHORT_CIRCUIT",
                    "Transformer vk_percent must be positive.",
                    "trafo",
                    int(idx),
                )

    try:
        from pandapower.topology import unsupplied_buses

        in_service_buses = (
            set(net.bus.index[net.bus.in_service])
            if "in_service" in net.bus
            else set(net.bus.index)
        )
        for idx in sorted(unsupplied_buses(net) & in_service_buses):
            add(
                "error",
                "DISCONNECTED_BUS",
                "In-service bus is not supplied by any source.",
                "bus",
                int(idx),
            )
    except ImportError:
        # pandapower is the owning package, but keep the structural audit usable
        # if its optional topology dependencies are unavailable.
        pass

    errors = sum(finding.severity == "error" for finding in findings)
    warnings = sum(finding.severity == "warning" for finding in findings)
    infos = sum(finding.severity == "info" for finding in findings)
    status = "error" if errors else "warning" if warnings else "ok"
    return AuditReport(
        status=status,
        counts={"errors": errors, "warnings": warnings, "info": infos},
        findings=findings,
    )
