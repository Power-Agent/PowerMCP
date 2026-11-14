"""Topology-aware N-1 security assessment for pandapower networks.

The assessment operates on private network copies. It uses pandapower's
switch-aware topology graph to identify load-bearing islands without a
voltage-controlling source before attempting an AC power flow.
"""
from __future__ import annotations

import copy
import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pandapower as pp
import pandapower.topology as topology
import networkx as nx


DEFAULT_CONTINGENCY_ELEMENTS = ("line", "trafo")


def _finite_number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _active_rows(net: Any, table: str) -> Iterable[Tuple[Any, Any]]:
    frame = net.get(table)
    if frame is None or not hasattr(frame, "iterrows") or "in_service" not in frame:
        return ()
    return ((idx, row) for idx, row in frame.iterrows() if bool(row.get("in_service", True)))


def _topology_islands(net: Any) -> List[Dict[str, Any]]:
    """Return graph components and classify islands with active load but no slack."""
    graph = topology.create_nxgraph(
        net,
        respect_switches=True,
        include_out_of_service=False,
        multi=True,
    )
    active_buses = set(
        net.bus.index[net.bus.in_service.astype(bool)]
    ) if "in_service" in net.bus else set(net.bus.index)
    graph.add_nodes_from(active_buses)

    sources = set()
    for _, row in _active_rows(net, "ext_grid"):
        sources.add(row["bus"])
    for _, row in _active_rows(net, "gen"):
        if bool(row.get("slack", False)):
            sources.add(row["bus"])

    loads_by_bus: Dict[Any, float] = {}
    for table in ("load", "sgen", "storage"):
        for _, row in _active_rows(net, table):
            p_mw = _finite_number(row.get("p_mw")) or 0.0
            # Only positive net consumption contributes to unsupplied demand.
            loads_by_bus[row["bus"]] = loads_by_bus.get(row["bus"], 0.0) + max(p_mw, 0.0)

    islands = []
    components = sorted(
        (set(component) for component in nx.connected_components(graph)),
        key=lambda component: (min(map(str, component)) if component else ""),
    )
    for component in components:
        load_mw = sum(loads_by_bus.get(bus, 0.0) for bus in component)
        island_sources = sorted((bus for bus in component if bus in sources), key=str)
        islands.append({
            "buses": sorted(component, key=str),
            "source_buses": island_sources,
            "load_mw": round(load_mw, 9),
            "supplied": bool(island_sources) or load_mw <= 1e-9,
        })
    return islands


def _limits(net: Any, table: str, row: Any, default: float) -> float:
    value = _finite_number(row.get("max_loading_percent"))
    if value is None:
        return default
    return value


def _evaluate_results(
    net: Any,
    *,
    voltage_min_pu: float,
    voltage_max_pu: float,
    line_loading_limit_percent: float,
    trafo_loading_limit_percent: float,
) -> Dict[str, Any]:
    voltage_violations = []
    if hasattr(net, "res_bus") and not net.res_bus.empty:
        for bus, result in net.res_bus.iterrows():
            if bus not in net.bus.index or not bool(net.bus.at[bus, "in_service"]):
                continue
            vm = _finite_number(result.get("vm_pu"))
            if vm is None:
                continue
            row = net.bus.loc[bus]
            lower = _finite_number(row.get("min_vm_pu"))
            upper = _finite_number(row.get("max_vm_pu"))
            lower = voltage_min_pu if lower is None else lower
            upper = voltage_max_pu if upper is None else upper
            if vm < lower:
                voltage_violations.append({"bus": bus, "vm_pu": vm, "limit_pu": lower, "kind": "undervoltage", "deviation_pu": round(lower - vm, 9)})
            elif vm > upper:
                voltage_violations.append({"bus": bus, "vm_pu": vm, "limit_pu": upper, "kind": "overvoltage", "deviation_pu": round(vm - upper, 9)})

    line_violations = []
    if hasattr(net, "res_line") and not net.res_line.empty:
        for idx, result in net.res_line.iterrows():
            if idx not in net.line.index or not bool(net.line.at[idx, "in_service"]):
                continue
            loading = _finite_number(result.get("loading_percent"))
            if loading is None:
                continue
            limit = _limits(net, "line", net.line.loc[idx], line_loading_limit_percent)
            if loading > limit:
                line_violations.append({"element": "line", "index": idx, "loading_percent": loading, "limit_percent": limit, "excess_percent": round(loading - limit, 9)})

    transformer_violations = []
    for table, result_table in (("trafo", "res_trafo"), ("trafo3w", "res_trafo3w")):
        if table not in net or result_table not in net or net[result_table].empty:
            continue
        for idx, result in net[result_table].iterrows():
            if idx not in net[table].index or not bool(net[table].at[idx, "in_service"]):
                continue
            loading = _finite_number(result.get("loading_percent"))
            if loading is None:
                continue
            limit = _limits(net, table, net[table].loc[idx], trafo_loading_limit_percent)
            if loading > limit:
                transformer_violations.append({"element": table, "index": idx, "loading_percent": loading, "limit_percent": limit, "excess_percent": round(loading - limit, 9)})

    max_thermal_excess = max(
        [item["excess_percent"] for item in line_violations + transformer_violations],
        default=0.0,
    )
    max_voltage_deviation = max(
        [item["deviation_pu"] for item in voltage_violations],
        default=0.0,
    )
    return {
        "voltage_violations": voltage_violations,
        "line_overloads": line_violations,
        "transformer_overloads": transformer_violations,
        "severity": {
            "unserved_load_mw": 0.0,
            "voltage_violation_count": len(voltage_violations),
            "max_voltage_deviation_pu": round(max_voltage_deviation, 9),
            "thermal_overload_count": len(line_violations) + len(transformer_violations),
            "max_thermal_excess_percent": round(max_thermal_excess, 9),
        },
    }


def run_security_assessment(
    net: Any,
    *,
    elements: Optional[Sequence[str]] = None,
    voltage_min_pu: float = 0.95,
    voltage_max_pu: float = 1.05,
    line_loading_limit_percent: float = 100.0,
    trafo_loading_limit_percent: float = 100.0,
    runpp_options: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Run deterministic single-element outages and quantify post-contingency security.

    Only N-1 is implemented. The default outage set deliberately preserves the
    historical line/two-winding-transformer scope; callers can request other
    pandapower element tables explicitly.
    """
    if not (math.isfinite(voltage_min_pu) and math.isfinite(voltage_max_pu) and voltage_min_pu < voltage_max_pu):
        raise ValueError("Voltage limits must be finite and voltage_min_pu must be below voltage_max_pu.")
    if not (math.isfinite(line_loading_limit_percent) and line_loading_limit_percent > 0):
        raise ValueError("line_loading_limit_percent must be finite and positive.")
    if not (math.isfinite(trafo_loading_limit_percent) and trafo_loading_limit_percent > 0):
        raise ValueError("trafo_loading_limit_percent must be finite and positive.")
    if runpp_options and not isinstance(runpp_options, Mapping):
        raise TypeError("runpp_options must be a mapping.")

    requested = tuple(DEFAULT_CONTINGENCY_ELEMENTS if elements is None else elements)
    if not requested:
        raise ValueError("At least one contingency element table must be selected.")
    unsupported = [name for name in requested if name not in net or "in_service" not in net[name].columns]
    if unsupported:
        raise ValueError(f"Unsupported contingency element table(s): {unsupported}")

    base_islands = _topology_islands(net)
    results = []
    for element_type in requested:
        for idx, _ in _active_rows(net, element_type):
            case = copy.deepcopy(net)
            case[element_type].at[idx, "in_service"] = False
            label = f"{element_type}_{idx}"
            try:
                islands = _topology_islands(case)
                unsupplied = [island for island in islands if not island["supplied"]]
                unserved_load = sum(island["load_mw"] for island in unsupplied)
                if unsupplied:
                    results.append({
                        "contingency": label,
                        "element": element_type,
                        "index": idx,
                        "converged": False,
                        "classification": "islanding",
                        "islands": islands,
                        "unsupplied_islands": unsupplied,
                        "violations": {
                            "voltage_violations": [],
                            "line_overloads": [],
                            "transformer_overloads": [],
                            "severity": {
                                "unserved_load_mw": round(unserved_load, 9),
                                "voltage_violation_count": 0,
                                "max_voltage_deviation_pu": 0.0,
                                "thermal_overload_count": 0,
                                "max_thermal_excess_percent": 0.0,
                            },
                        },
                    })
                    continue

                pp.runpp(case, **dict(runpp_options or {}))
                if not bool(getattr(case, "converged", False)):
                    results.append({
                        "contingency": label,
                        "element": element_type,
                        "index": idx,
                        "converged": False,
                        "classification": "power_flow_nonconvergence",
                        "islands": islands,
                        "violations": None,
                    })
                    continue
                violations = _evaluate_results(
                    case,
                    voltage_min_pu=voltage_min_pu,
                    voltage_max_pu=voltage_max_pu,
                    line_loading_limit_percent=line_loading_limit_percent,
                    trafo_loading_limit_percent=trafo_loading_limit_percent,
                )
                results.append({
                    "contingency": label,
                    "element": element_type,
                    "index": idx,
                    "converged": True,
                    "classification": "secure" if not any((
                        violations["voltage_violations"],
                        violations["line_overloads"],
                        violations["transformer_overloads"],
                    )) else "limit_violations",
                    "islands": islands,
                    "violations": violations,
                })
            except Exception as exc:
                results.append({
                    "contingency": label,
                    "element": element_type,
                    "index": idx,
                    "converged": False,
                    "classification": "analysis_error",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    # Stable, transparent ordering: islanding/unserved load first, then
    # limit violations by counts and magnitudes, then solver/error outcomes.
    def rank(item: Dict[str, Any]) -> Tuple[float, int, float, int, str]:
        severity = ((item.get("violations") or {}).get("severity") or {})
        return (
            -float(severity.get("unserved_load_mw", 0.0)),
            -int(severity.get("voltage_violation_count", 0)) - int(severity.get("thermal_overload_count", 0)),
            -float(severity.get("max_voltage_deviation_pu", 0.0)) - float(severity.get("max_thermal_excess_percent", 0.0)),
            0 if item["classification"] == "islanding" else 1,
            item["contingency"],
        )
    results.sort(key=rank)
    return {
        "status": "success",
        "analysis_type": "N-1",
        "base_islands": base_islands,
        "contingency_count": len(results),
        "summary": {
            "secure": sum(item["classification"] == "secure" for item in results),
            "limit_violations": sum(item["classification"] == "limit_violations" for item in results),
            "islanding": sum(item["classification"] == "islanding" for item in results),
            "nonconvergent": sum(item["classification"] == "power_flow_nonconvergence" for item in results),
            "errors": sum(item["classification"] == "analysis_error" for item in results),
        },
        "results": results,
    }
