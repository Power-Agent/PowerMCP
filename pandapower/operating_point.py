"""Deterministic validation of a solved pandapower operating point."""

from __future__ import annotations

import math
from typing import Any, Dict


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _near(margin: float, scale: float) -> bool:
    """True when an element is within 5% of a limit it does not yet violate."""
    return 0 <= margin and margin / scale < 0.05


def _finding(code: str, element: str, index: Any, value: Any, limit: float) -> Dict[str, Any]:
    return {
        "severity": "error",
        "code": code,
        "element": element,
        "index": index,
        "metric": "vm_pu" if "VOLTAGE" in code else "loading_percent",
        "value": float(value) if _finite(value) else None,
        "limit": float(limit),
    }


def validate_operating_point(
    net: Any,
    *,
    voltage_min_pu: float = 0.95,
    voltage_max_pu: float = 1.05,
    line_loading_limit_percent: float = 100.0,
    trafo_loading_limit_percent: float = 100.0,
) -> Dict[str, Any]:
    """Validate existing power-flow results without solving or mutating net."""
    criteria = {
        "voltage_min_pu": voltage_min_pu,
        "voltage_max_pu": voltage_max_pu,
        "line_loading_limit_percent": line_loading_limit_percent,
        "trafo_loading_limit_percent": trafo_loading_limit_percent,
    }
    if not all(_finite(v) for v in criteria.values()):
        return {
            "status": "failed",
            "message": "All validation limits must be finite.",
            "criteria": {k: (float(v) if _finite(v) else None) for k, v in criteria.items()},
        }
    if not (0 <= voltage_min_pu < voltage_max_pu):
        return {"status": "failed", "message": "Require 0 <= voltage_min_pu < voltage_max_pu.", "criteria": criteria}
    if line_loading_limit_percent <= 0 or trafo_loading_limit_percent <= 0:
        return {"status": "failed", "message": "Loading limits must be positive.", "criteria": criteria}

    try:
        res_bus = net.res_bus
        res_line = net.res_line
        res_trafo = net.res_trafo
    except AttributeError as exc:
        return {"status": "failed", "message": f"Operating-point results are unavailable: {exc}", "criteria": criteria}

    # pandapower can expose a truthy/default converged flag before a power
    # flow has populated result tables. Require both the flag and actual bus
    # results so a fresh network cannot be mistaken for a solved operating point.
    if not bool(getattr(net, "converged", False)) or res_bus.empty:
        return {"status": "failed", "message": "No converged power-flow result is available.", "criteria": criteria}

    try:
        if "vm_pu" not in res_bus:
            return {"status": "failed", "message": "Bus voltage results are unavailable.", "criteria": criteria}

        # pandapower reports NaN voltages for buses switched out of service by
        # design; only in-service buses are checked, so a NaN left over there
        # still means the bus lost supply.
        bus = getattr(net, "bus", None)
        oos = set(bus.index[~bus["in_service"].astype(bool)]) if bus is not None and "in_service" in bus else set()
        vm_series = res_bus["vm_pu"][~res_bus.index.isin(oos)]

        violations = []
        vm_values = [float(v) for v in vm_series if _finite(v)]
        for idx, value in vm_series.items():
            if not _finite(value):
                violations.append(_finding("NONFINITE_BUS_VOLTAGE", "bus", idx, value, voltage_min_pu))
            elif float(value) < voltage_min_pu:
                violations.append(_finding("BUS_UNDERVOLTAGE", "bus", idx, float(value), voltage_min_pu))
            elif float(value) > voltage_max_pu:
                violations.append(_finding("BUS_OVERVOLTAGE", "bus", idx, float(value), voltage_max_pu))

        line_values = []
        for idx, value in res_line["loading_percent"].items() if "loading_percent" in res_line else []:
            if _finite(value):
                line_values.append(float(value))
                if float(value) > line_loading_limit_percent:
                    violations.append(_finding("LINE_OVERLOAD", "line", idx, float(value), line_loading_limit_percent))

        trafo_values = []
        for idx, value in res_trafo["loading_percent"].items() if "loading_percent" in res_trafo else []:
            if _finite(value):
                trafo_values.append(float(value))
                if float(value) > trafo_loading_limit_percent:
                    violations.append(_finding("TRAFO_OVERLOAD", "trafo", idx, float(value), trafo_loading_limit_percent))

        res_trafo3w = getattr(net, "res_trafo3w", None)
        if res_trafo3w is not None and "loading_percent" in res_trafo3w:
            for idx, value in res_trafo3w["loading_percent"].items():
                if _finite(value):
                    trafo_values.append(float(value))
                    if float(value) > trafo_loading_limit_percent:
                        violations.append(
                            _finding("TRAFO3W_OVERLOAD", "trafo3w", idx, float(value), trafo_loading_limit_percent)
                        )

        min_vm = min(vm_values) if vm_values else None
        max_vm = max(vm_values) if vm_values else None
        max_line = max(line_values) if line_values else None
        max_trafo = max(trafo_values) if trafo_values else None

        near_limit = []
        voltage_band = voltage_max_pu - voltage_min_pu
        if any(_near(v - voltage_min_pu, voltage_band) or _near(voltage_max_pu - v, voltage_band) for v in vm_values):
            near_limit.append("BUS_VOLTAGE_NEAR_LIMIT")
        if any(_near(line_loading_limit_percent - v, line_loading_limit_percent) for v in line_values):
            near_limit.append("LINE_LOADING_NEAR_LIMIT")
        if any(_near(trafo_loading_limit_percent - v, trafo_loading_limit_percent) for v in trafo_values):
            near_limit.append("TRAFO_LOADING_NEAR_LIMIT")

        p_loss_mw = sum(float(v) for v in res_line["pl_mw"]) if "pl_mw" in res_line else 0.0
        q_loss_mvar = sum(float(v) for v in res_line["ql_mvar"]) if "ql_mvar" in res_line else 0.0
        if "pl_mw" in res_trafo:
            p_loss_mw += sum(float(v) for v in res_trafo["pl_mw"])
        if "ql_mvar" in res_trafo:
            q_loss_mvar += sum(float(v) for v in res_trafo["ql_mvar"])
        if res_trafo3w is not None and "pl_mw" in res_trafo3w:
            p_loss_mw += sum(float(v) for v in res_trafo3w["pl_mw"])
        if res_trafo3w is not None and "ql_mvar" in res_trafo3w:
            q_loss_mvar += sum(float(v) for v in res_trafo3w["ql_mvar"])

        violations.sort(key=lambda x: (x["code"], str(x["element"]), str(x["index"])))
        return {
            "status": "error" if violations else ("warning" if near_limit else "ok"),
            "converged": True,
            "criteria": criteria,
            "summary": {
                "min_vm_pu": min_vm,
                "max_vm_pu": max_vm,
                "max_line_loading_percent": max_line,
                "max_trafo_loading_percent": max_trafo,
                "p_loss_mw": p_loss_mw,
                "q_loss_mvar": q_loss_mvar,
            },
            "near_limit_codes": sorted(set(near_limit)),
            "violations": violations,
            "counts": {"errors": len(violations), "warnings": len(set(near_limit))},
        }
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "failed", "message": f"Operating-point validation failed: {exc}", "criteria": criteria}
