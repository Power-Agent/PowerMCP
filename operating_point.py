"""Deterministic validation of a solved pandapower operating point."""

from __future__ import annotations

import math
from typing import Any, Dict


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _finding(code: str, element: str, index: Any, value: float, limit: float) -> Dict[str, Any]:
    return {
        "severity": "error",
        "code": code,
        "element": element,
        "index": index,
        "metric": "vm_pu" if "VOLTAGE" in code else "loading_percent",
        "value": float(value),
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
        return {"status": "failed", "message": "All validation limits must be finite.", "criteria": criteria}
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

        violations = []
        vm_values = [float(v) for v in res_bus["vm_pu"] if _finite(v)]
        for idx, value in res_bus["vm_pu"].items():
            if not _finite(value):
                violations.append(_finding("NONFINITE_BUS_VOLTAGE", "bus", idx, float("nan"), voltage_min_pu))
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

        min_vm = min(vm_values) if vm_values else None
        max_vm = max(vm_values) if vm_values else None
        max_line = max(line_values) if line_values else None
        max_trafo = max(trafo_values) if trafo_values else None

        near_limit = []
        voltage_band = voltage_max_pu - voltage_min_pu
        if min_vm is not None and (min_vm - voltage_min_pu) / voltage_band < 0.05:
            near_limit.append("BUS_VOLTAGE_NEAR_LIMIT")
        if max_vm is not None and (voltage_max_pu - max_vm) / voltage_band < 0.05:
            near_limit.append("BUS_VOLTAGE_NEAR_LIMIT")
        if max_line is not None and (line_loading_limit_percent - max_line) / line_loading_limit_percent < 0.05:
            near_limit.append("LINE_LOADING_NEAR_LIMIT")
        if max_trafo is not None and (trafo_loading_limit_percent - max_trafo) / trafo_loading_limit_percent < 0.05:
            near_limit.append("TRAFO_LOADING_NEAR_LIMIT")

        p_loss_mw = sum(float(v) for v in res_line["pl_mw"]) if "pl_mw" in res_line else 0.0
        q_loss_mvar = sum(float(v) for v in res_line["ql_mvar"]) if "ql_mvar" in res_line else 0.0
        if "pl_mw" in res_trafo:
            p_loss_mw += sum(float(v) for v in res_trafo["pl_mw"])
        if "ql_mvar" in res_trafo:
            q_loss_mvar += sum(float(v) for v in res_trafo["ql_mvar"])

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
