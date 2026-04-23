"""Surge MCP server.

Exposes surge (surge-py v0.1.5+) to LLM agents via the Model Context
Protocol. Tools span ten categories: case I/O, power flow, DC
sensitivities, OPF, contingency analysis, transfer capability, dispatch,
inspection, export & graph analytics, and network construction /
editing.

Conventions (shared with peer PowerMCP tools):
  * Every tool returns ``{"status": "success"|"error", "message": str,
    "results"?: dict}`` — strict shape so callers can always detect error
    conditions.
  * Network and last-PF state live in module-level globals so subsequent
    tools can operate on the loaded case without reloading.
  * Solution objects are serialized via surge's ``to_dict()`` helpers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import surge
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Initializing Surge Analysis Server")
mcp = FastMCP("Surge Analysis Server")

# ---------------------------------------------------------------------------
# Global state — a single loaded network per server instance, plus the most
# recent PF/OPF solution so inspection tools can report solved values
# without re-solving.
# ---------------------------------------------------------------------------
_current_net: Optional[surge.Network] = None
_last_pf_result: Any = None


def _require_network() -> surge.Network:
    """Return the currently loaded network or raise RuntimeError if none."""
    if _current_net is None:
        raise RuntimeError(
            "no network loaded — call load_network, load_builtin_case, or "
            "create from scratch before running analysis tools"
        )
    return _current_net


def _ok(message: str, results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a success-shaped return dict."""
    out: Dict[str, Any] = {"status": "success", "message": message}
    if results is not None:
        out["results"] = results
    return out


def _err(message: str) -> Dict[str, Any]:
    """Build an error-shaped return dict."""
    return {"status": "error", "message": message}


def _find_branch_index(net: surge.Network, key: Tuple[int, int, str]) -> int:
    """Look up a branch by (from_bus, to_bus, circuit) tuple.

    Raises ValueError if the triple does not match any in-service branch.
    """
    from_bus, to_bus, circuit = key
    return net.branch_index(from_bus, to_bus, circuit)


# ---------------------------------------------------------------------------
# Category 1: Case I/O
# ---------------------------------------------------------------------------

@mcp.tool()
def load_network(file_path: str, format: Optional[str] = None) -> Dict[str, Any]:
    """Load a network from a file.

    Args:
        file_path: Path to the case file. Supported extensions auto-detect
            the format (``.surge.json.zst``, ``.m``, ``.raw``, ``.rawx``,
            ``.xiidm``, ``.uct``, ``.dss``, ``.epc``).
        format: Optional explicit format override when extension detection
            is ambiguous. One of: ``matpower``, ``psse``, ``rawx``,
            ``xiidm``, ``ucte``, ``surge-json``, ``surge-bin``, ``dss``,
            ``epc``.

    Returns:
        {"status", "message", "results": {network summary}}.
    """
    global _current_net, _last_pf_result
    try:
        _current_net = surge.load(file_path, format=format) if format else surge.load(file_path)
        _last_pf_result = None
        return _ok(
            f"network loaded from {file_path}",
            _current_net.summary(),
        )
    except FileNotFoundError:
        return _err(f"file not found: {file_path}")
    except Exception as exc:
        return _err(f"failed to load network: {exc}")


@mcp.tool()
def save_network(file_path: str) -> Dict[str, Any]:
    """Save the currently loaded network to disk.

    Format is auto-detected from the file extension.

    Args:
        file_path: Destination path. Extension determines the format.

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        surge.save(net, file_path)
        return _ok(f"network saved to {file_path}")
    except Exception as exc:
        return _err(f"failed to save network: {exc}")


@mcp.tool()
def load_builtin_case(name: str) -> Dict[str, Any]:
    """Load an embedded benchmark case by name.

    Args:
        name: One of the values listed in the error message when an
            invalid name is supplied (e.g. ``case9``, ``case14``,
            ``case30``, ``case57``, ``case118``, ``case300``,
            ``market30``). Full list available via
            ``surge.list_builtin_cases()``.

    Returns:
        {"status", "message", "results": {"available": [...], "summary": {...}}}.
    """
    global _current_net, _last_pf_result
    try:
        _current_net = surge.load_builtin_case(name)
        _last_pf_result = None
        return _ok(
            f"builtin case '{name}' loaded",
            {
                "available": list(surge.list_builtin_cases()),
                "summary": _current_net.summary(),
            },
        )
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"failed to load builtin case: {exc}")


@mcp.tool()
def get_network_info() -> Dict[str, Any]:
    """Return a comprehensive summary of the loaded network.

    Includes element counts (buses, branches, generators, loads, shunts,
    HVDC links), totals (generation, generation capacity, load P/Q),
    areas, zones, and unique voltage levels.

    Returns:
        {"status", "message", "results": <surge Network.summary() dict>}.
    """
    try:
        net = _require_network()
        return _ok("network summary retrieved", net.summary())
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"failed to retrieve network info: {exc}")


# ---------------------------------------------------------------------------
# Category 2: Power flow
# ---------------------------------------------------------------------------

@mcp.tool()
def run_ac_power_flow(
    flat_start: bool = False,
    enforce_q_limits: bool = False,
    max_iterations: int = 30,
    tolerance: float = 1e-8,
) -> Dict[str, Any]:
    """Solve Newton-Raphson AC power flow on the loaded network.

    Args:
        flat_start: If True, start from 1.0 p.u. voltages and 0 rad angles
            rather than any stored solution.
        enforce_q_limits: If True, switch PV buses to PQ when reactive
            limits are exceeded.
        max_iterations: Hard cap on Newton iterations.
        tolerance: Mismatch convergence tolerance (power units).

    Returns:
        {"status", "message", "results": <AcPfResult.to_dict()>}.
    """
    global _last_pf_result
    try:
        net = _require_network()
        opts = surge.AcPfOptions(
            flat_start=flat_start,
            enforce_q_limits=enforce_q_limits,
            max_iterations=max_iterations,
            tolerance=tolerance,
        )
        sol = surge.solve_ac_pf(net, opts)
        _last_pf_result = sol
        return _ok(
            f"AC power flow {'converged' if sol.converged else 'did NOT converge'}"
            f" in {sol.iterations} iterations",
            sol.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"AC power flow failed: {exc}")


@mcp.tool()
def run_dc_power_flow(headroom_slack: bool = False) -> Dict[str, Any]:
    """Solve DC (lossless linearized) power flow on the loaded network.

    Args:
        headroom_slack: If True, distribute slack across generators
            weighted by online headroom instead of using a single slack
            bus.

    Returns:
        {"status", "message", "results": <DcPfResult.to_dict()>}.
    """
    global _last_pf_result
    try:
        net = _require_network()
        opts = surge.DcPfOptions(headroom_slack=headroom_slack)
        sol = surge.solve_dc_pf(net, opts)
        _last_pf_result = sol
        return _ok("DC power flow solved", sol.to_dict())
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"DC power flow failed: {exc}")


@mcp.tool()
def run_fast_decoupled_pf(variant: str = "xb") -> Dict[str, Any]:
    """Solve fast-decoupled AC power flow.

    Args:
        variant: ``xb`` (default) or ``bx`` — controls which Jacobian
            approximation is used. ``xb`` is Stott & Alsac's original;
            ``bx`` is Van Amerongen's variant that handles high-R/X lines
            better.

    Returns:
        {"status", "message", "results": <AcPfResult.to_dict()>}.
    """
    global _last_pf_result
    try:
        from surge.powerflow import FdpfOptions, solve_fdpf
        net = _require_network()
        sol = solve_fdpf(net, FdpfOptions(variant=variant))
        _last_pf_result = sol
        n_switches = getattr(sol, "n_q_limit_switches", 0)
        switch_note = (
            f" across {n_switches} Q-limit switch(es)"
            if n_switches
            else ""
        )
        return _ok(
            f"FDPF ({variant}) {'converged' if sol.converged else 'did NOT converge'}"
            f" in {sol.iterations} iterations{switch_note} "
            f"(max_mismatch={sol.max_mismatch:.2e})",
            sol.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"fast-decoupled power flow failed: {exc}")


# ---------------------------------------------------------------------------
# Category 3: DC sensitivities
# ---------------------------------------------------------------------------

@mcp.tool()
def compute_ptdf(
    monitored_branches: Optional[List[Tuple[int, int, str]]] = None,
    format: str = "summary",
    top_k_per_branch: int = 10,
) -> Dict[str, Any]:
    """Compute Power Transfer Distribution Factors for the loaded network.

    Args:
        monitored_branches: Optional list of ``(from_bus, to_bus, circuit)``
            tuples to filter the matrix rows. Default: all in-service
            branches.
        format: ``summary`` (default, bounded output — safe for large
            networks), ``sparse`` (CSR triple), or ``full`` (dense nested
            list).
        top_k_per_branch: For ``summary``, the largest-|value| bus entries
            retained per monitored branch.

    Returns:
        {"status", "message", "results": <PtdfResult.to_dict()>}.
    """
    try:
        from surge.dc import BranchKey, PtdfRequest, compute_ptdf as _compute
        net = _require_network()
        request = None
        if monitored_branches:
            keys = tuple(
                BranchKey(from_bus=f, to_bus=t, circuit=c)
                for (f, t, c) in monitored_branches
            )
            request = PtdfRequest(monitored_branches=keys)
        res = _compute(net, request)
        n_monitored, n_buses = res.ptdf.shape
        return _ok(
            f"PTDF computed ({n_monitored} × {n_buses})",
            res.to_dict(format=format, top_k_per_branch=top_k_per_branch),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"PTDF computation failed: {exc}")


@mcp.tool()
def compute_lodf(
    outage_branches: Optional[List[Tuple[int, int, str]]] = None,
    monitored_branches: Optional[List[Tuple[int, int, str]]] = None,
    format: str = "summary",
    top_k_per_branch: int = 10,
) -> Dict[str, Any]:
    """Compute Line Outage Distribution Factors.

    Args:
        outage_branches: Optional list of ``(from_bus, to_bus, circuit)``
            triples defining outage columns. Default: all in-service
            branches.
        monitored_branches: Optional list of branches to monitor
            (rows). Default: all in-service branches.
        format: ``summary`` (default), ``sparse``, or ``full``.
        top_k_per_branch: For ``summary``, number of largest-|value|
            outage entries retained per monitored branch.

    Returns:
        {"status", "message", "results": <LodfResult.to_dict()>}.
    """
    try:
        from surge.dc import BranchKey, LodfRequest, compute_lodf as _compute
        net = _require_network()
        request = None
        if monitored_branches or outage_branches:
            mk = tuple(
                BranchKey(from_bus=f, to_bus=t, circuit=c)
                for (f, t, c) in (monitored_branches or [])
            ) or None
            ok = tuple(
                BranchKey(from_bus=f, to_bus=t, circuit=c)
                for (f, t, c) in (outage_branches or [])
            ) or None
            request = LodfRequest(monitored_branches=mk, outage_branches=ok)
        res = _compute(net, request)
        n_monitored, n_outages = res.lodf.shape
        return _ok(
            f"LODF computed ({n_monitored} × {n_outages})",
            res.to_dict(format=format, top_k_per_branch=top_k_per_branch),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"LODF computation failed: {exc}")


@mcp.tool()
def compute_otdf(
    outage_branches: List[Tuple[int, int, str]],
    monitored_branches: List[Tuple[int, int, str]],
    format: str = "summary",
    top_k_per_pair: int = 10,
) -> Dict[str, Any]:
    """Compute Outage Transfer Distribution Factors.

    OTDF is a 3-D tensor ``(n_monitored, n_outages, n_buses)``. Because
    dense dumps are almost always impractical, this tool refuses
    ``format="full"`` and steers callers to ``summary`` or ``sparse``.

    Args:
        outage_branches: Required list of ``(from_bus, to_bus, circuit)``
            tuples for outage scenarios.
        monitored_branches: Required list of branches to monitor.
        format: ``summary`` (default, top-k buses per monitored/outage
            pair) or ``sparse`` (coordinate list of non-zero entries).
        top_k_per_pair: For ``summary``, number of largest-|value| bus
            entries retained per (monitored, outage) pair.

    Returns:
        {"status", "message", "results": <OtdfResult.to_dict()>}.
    """
    try:
        from surge.dc import BranchKey, OtdfRequest, compute_otdf as _compute
        net = _require_network()
        req = OtdfRequest(
            monitored_branches=tuple(
                BranchKey(from_bus=f, to_bus=t, circuit=c)
                for (f, t, c) in monitored_branches
            ),
            outage_branches=tuple(
                BranchKey(from_bus=f, to_bus=t, circuit=c)
                for (f, t, c) in outage_branches
            ),
        )
        res = _compute(net, req)
        n_monitored, n_outages, n_buses = res.otdf.shape
        return _ok(
            f"OTDF computed ({n_monitored} × {n_outages} × {n_buses})",
            res.to_dict(format=format, top_k_per_pair=top_k_per_pair),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"OTDF computation failed: {exc}")


# ---------------------------------------------------------------------------
# Category 4: Optimal power flow
# ---------------------------------------------------------------------------

@mcp.tool()
def run_dc_opf(lp_solver: str = "default") -> Dict[str, Any]:
    """Solve DC optimal power flow.

    Args:
        lp_solver: One of ``default`` (auto-detect best available),
            ``highs``, ``gurobi``, ``copt``, ``cplex``. HiGHS is the
            open-source fallback.

    Returns:
        {"status", "message", "results": <DcOpfResult.to_dict()>}.
    """
    try:
        from surge.opf import DcOpfOptions, DcOpfRuntime, solve_dc_opf as _solve
        net = _require_network()
        runtime = DcOpfRuntime(
            lp_solver=None if lp_solver == "default" else lp_solver
        )
        sol = _solve(net, DcOpfOptions(), runtime)
        return _ok(
            f"DC-OPF solved (cost={sol.opf.total_cost:.2f}, "
            f"feasible={sol.feasible})",
            sol.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"DC-OPF failed: {exc}")


@mcp.tool()
def run_ac_opf(nlp_solver: str = "default") -> Dict[str, Any]:
    """Solve AC optimal power flow.

    Args:
        nlp_solver: One of ``default`` (auto-detect), ``ipopt``,
            ``copt``, ``gurobi``. Ipopt is the open-source fallback.

    Returns:
        {"status", "message", "results": <AcOpfResult.to_dict()>}.
    """
    try:
        from surge.opf import AcOpfOptions, AcOpfRuntime, solve_ac_opf as _solve
        net = _require_network()
        runtime = AcOpfRuntime(
            nlp_solver=None if nlp_solver == "default" else nlp_solver
        )
        sol = _solve(net, AcOpfOptions(), runtime)
        return _ok(
            f"AC-OPF solved (cost={sol.opf.total_cost:.2f}, "
            f"converged={sol.opf.converged})",
            sol.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"AC-OPF failed: {exc}")


@mcp.tool()
def run_scopf(
    lp_solver: str = "default",
    nlp_solver: str = "default",
) -> Dict[str, Any]:
    """Solve Security-Constrained Optimal Power Flow with N-1 screening.

    Args:
        lp_solver: LP/MIP backend — ``default``, ``highs``, ``gurobi``,
            ``copt``, ``cplex``.
        nlp_solver: NLP backend for the AC formulation — ``default``,
            ``ipopt``, ``copt``, ``gurobi``.

    Returns:
        {"status", "message", "results": <ScopfResult.to_dict()>}.
    """
    try:
        from surge.opf import ScopfOptions, ScopfRuntime, solve_scopf as _solve
        net = _require_network()
        runtime = ScopfRuntime(
            lp_solver=None if lp_solver == "default" else lp_solver,
            nlp_solver=None if nlp_solver == "default" else nlp_solver,
        )
        sol = _solve(net, ScopfOptions(), runtime)
        return _ok(
            f"SCOPF solved (converged={sol.converged}, "
            f"iterations={sol.iterations}, "
            f"contingency_constraints={sol.total_contingency_constraints})",
            sol.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"SCOPF failed: {exc}")


# ---------------------------------------------------------------------------
# Category 5: Contingency analysis
# ---------------------------------------------------------------------------

@mcp.tool()
def run_n1_branch_contingency(
    monitored_branches: Optional[List[Tuple[int, int, str]]] = None,
) -> Dict[str, Any]:
    """Run N-1 branch contingency analysis on the loaded network.

    Args:
        monitored_branches: Optional list of ``(from_bus, to_bus, circuit)``
            triples restricting the monitored set. Default: all in-service
            branches.

    Returns:
        {"status", "message", "results": <ContingencyAnalysis.to_dict()>}.
    """
    try:
        net = _require_network()
        ca = surge.analyze_n1_branch(net)
        d = ca.to_dict()
        if monitored_branches:
            allowed = {(f, t, str(c)) for (f, t, c) in monitored_branches}
            d["violations"] = [
                v
                for v in d["violations"]
                if (v.get("from_bus"), v.get("to_bus")) not in {(None, None)}
                and any(
                    a == v.get("from_bus") and b == v.get("to_bus")
                    for (a, b, _c) in allowed
                )
            ]
        return _ok(
            f"N-1 branch analysis: {d['n_contingencies']} scenarios, "
            f"{d['n_with_violations']} with violations",
            d,
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"N-1 branch contingency failed: {exc}")


@mcp.tool()
def run_n1_generator_contingency() -> Dict[str, Any]:
    """Run N-1 generator contingency analysis on the loaded network.

    Returns:
        {"status", "message", "results": <ContingencyAnalysis.to_dict()>}.
    """
    try:
        net = _require_network()
        ca = surge.analyze_n1_generator(net)
        d = ca.to_dict()
        return _ok(
            f"N-1 generator analysis: {d['n_contingencies']} scenarios, "
            f"{d['n_with_violations']} with violations",
            d,
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"N-1 generator contingency failed: {exc}")


@mcp.tool()
def run_n2_branch_contingency() -> Dict[str, Any]:
    """Run N-2 branch contingency analysis on the loaded network.

    Returns:
        {"status", "message", "results": <ContingencyAnalysis.to_dict()>}.
    """
    try:
        net = _require_network()
        ca = surge.analyze_n2_branch(net)
        d = ca.to_dict()
        return _ok(
            f"N-2 branch analysis: {d['n_contingencies']} pairs, "
            f"{d['n_with_violations']} with violations",
            d,
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"N-2 branch contingency failed: {exc}")


# ---------------------------------------------------------------------------
# Category 6: Transfer capability
# ---------------------------------------------------------------------------

@mcp.tool()
def compute_nerc_atc(
    source_buses: List[int],
    sink_buses: List[int],
    name: str = "atc",
    trm_fraction: float = 0.05,
    cbm_mw: float = 0.0,
    etc_mw: float = 0.0,
) -> Dict[str, Any]:
    """Compute NERC Available Transfer Capability (MOD-029 / MOD-030).

    Args:
        source_buses: List of bus numbers forming the source side of the
            transfer path.
        sink_buses: List of bus numbers forming the sink side.
        name: Descriptive label for the transfer path.
        trm_fraction: Transmission Reliability Margin as fraction of TTC
            (default 5%).
        cbm_mw: Capacity Benefit Margin in MW.
        etc_mw: Existing Transmission Commitments in MW.

    Returns:
        {"status", "message", "results": <NercAtcResult.to_dict()>}.
    """
    try:
        from surge import transfer
        net = _require_network()
        path = transfer.TransferPath(name, source_buses, sink_buses)
        options = transfer.AtcOptions(
            trm_fraction=trm_fraction,
            cbm_mw=cbm_mw,
            etc_mw=etc_mw,
        )
        res = transfer.compute_nerc_atc(net, path, options)
        return _ok(
            f"NERC ATC computed: {res.atc_mw:.1f} MW "
            f"(TTC={res.ttc_mw:.1f}, limit={res.limit_cause})",
            res.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"NERC ATC failed: {exc}")


@mcp.tool()
def compute_ac_atc(
    source_buses: List[int],
    sink_buses: List[int],
    name: str = "ac-atc",
    v_min: float = 0.95,
    v_max: float = 1.05,
) -> Dict[str, Any]:
    """Compute AC-aware Available Transfer Capability.

    Args:
        source_buses: List of bus numbers forming the source side.
        sink_buses: List of bus numbers forming the sink side.
        name: Descriptive label for the transfer path.
        v_min: Minimum allowable bus voltage in p.u. (default 0.95).
        v_max: Maximum allowable bus voltage in p.u. (default 1.05).

    Returns:
        {"status", "message", "results": <AcAtcResult.to_dict()>}.
    """
    try:
        from surge import transfer
        net = _require_network()
        path = transfer.TransferPath(name, source_buses, sink_buses)
        res = transfer.compute_ac_atc(net, path, v_min, v_max)
        return _ok(
            f"AC ATC computed: {res.atc_mw:.1f} MW "
            f"(limit={res.limiting_constraint})",
            res.to_dict(),
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"AC ATC failed: {exc}")


# ---------------------------------------------------------------------------
# Category 7: Dispatch (SCED / SCUC)
# ---------------------------------------------------------------------------

@mcp.tool()
def run_sced(
    request: Optional[Dict[str, Any]] = None,
    lp_solver: str = "default",
) -> Dict[str, Any]:
    """Solve single-period Security-Constrained Economic Dispatch.

    Args:
        request: Optional dispatch request as a dict. When ``None``, a
            default single-period DC SCED is run with all generators
            committed.
        lp_solver: ``default``, ``highs``, ``gurobi``, ``copt``, or
            ``cplex``. HiGHS is the open-source fallback.

    Returns:
        {"status", "message", "results": <DispatchResult.to_dict()>}.
    """
    try:
        from surge.dispatch import solve_dispatch
        net = _require_network()
        solver = None if lp_solver == "default" else lp_solver
        result = solve_dispatch(net, request, lp_solver=solver)
        return _ok("SCED solved", result.to_dict())
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"SCED failed: {exc}")


@mcp.tool()
def run_scuc(
    request: Optional[Dict[str, Any]] = None,
    lp_solver: str = "default",
) -> Dict[str, Any]:
    """Solve Security-Constrained Unit Commitment (multi-period MIP).

    Args:
        request: Optional dispatch request dict encoding multi-period
            scheduling with commitment decisions. Required for a true
            SCUC run; when ``None`` the solver falls back to a single-
            period LP.
        lp_solver: ``default``, ``highs``, ``gurobi``, ``copt``, or
            ``cplex``.

    Returns:
        {"status", "message", "results": <DispatchResult.to_dict()>}.
    """
    try:
        from surge.dispatch import solve_dispatch
        net = _require_network()
        solver = None if lp_solver == "default" else lp_solver
        result = solve_dispatch(net, request, lp_solver=solver)
        return _ok("SCUC solved", result.to_dict())
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"SCUC failed: {exc}")


# ---------------------------------------------------------------------------
# Category 8: Inspection
# ---------------------------------------------------------------------------

def _try_dataframe_records(df_or_dict: Any, limit: Optional[int]) -> List[Dict[str, Any]]:
    """Convert a DataFrame-or-dict return value into a list of row dicts.

    Handles both pandas-available and dict-fallback cases.
    """
    try:
        import pandas as pd

        if isinstance(df_or_dict, pd.DataFrame):
            df = df_or_dict.reset_index()
            if limit is not None:
                df = df.head(limit)
            return df.to_dict(orient="records")
    except ImportError:
        pass
    if isinstance(df_or_dict, dict):
        # parallel-column dict — zip into records
        keys = list(df_or_dict.keys())
        columns = [df_or_dict[k] for k in keys]
        n = min(len(col) for col in columns) if columns else 0
        if limit is not None:
            n = min(n, limit)
        return [
            {k: columns[i][row] for i, k in enumerate(keys)}
            for row in range(n)
        ]
    return []


@mcp.tool()
def list_buses(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """Enumerate buses with their metadata and (if available) solved
    voltages.

    Args:
        limit: Maximum number of buses to return. ``None`` returns all.
        sort_by: Optional column name to sort by
            (e.g. ``base_kv``, ``vm_pu``, ``pd_mw``). ``None`` preserves
            the native bus ordering.
        ascending: Sort direction when ``sort_by`` is set.

    Returns:
        {"status", "message", "results": {"count": int, "buses": [...]}}.
    """
    try:
        net = _require_network()
        df_or_dict = net.bus_dataframe()
        try:
            import pandas as pd
            if isinstance(df_or_dict, pd.DataFrame):
                df = df_or_dict.reset_index()
                if sort_by and sort_by in df.columns:
                    df = df.sort_values(sort_by, ascending=ascending)
                if limit is not None:
                    df = df.head(limit)
                records = df.to_dict(orient="records")
            else:
                records = _try_dataframe_records(df_or_dict, limit)
        except ImportError:
            records = _try_dataframe_records(df_or_dict, limit)
        return _ok(
            f"{len(records)} bus rows returned",
            {"count": len(records), "buses": records},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"list_buses failed: {exc}")


@mcp.tool()
def list_branches(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ascending: bool = True,
) -> Dict[str, Any]:
    """Enumerate branches with their metadata.

    Args:
        limit: Maximum rows to return. ``None`` returns all.
        sort_by: Optional column name (e.g. ``rate_a_mva``, ``x``,
            ``from_bus``). ``None`` preserves native branch ordering.
        ascending: Sort direction.

    Returns:
        {"status", "message", "results": {"count": int, "branches": [...]}}.
    """
    try:
        net = _require_network()
        df_or_dict = net.branch_dataframe()
        try:
            import pandas as pd
            if isinstance(df_or_dict, pd.DataFrame):
                df = df_or_dict.reset_index()
                if sort_by and sort_by in df.columns:
                    df = df.sort_values(sort_by, ascending=ascending)
                if limit is not None:
                    df = df.head(limit)
                records = df.to_dict(orient="records")
            else:
                records = _try_dataframe_records(df_or_dict, limit)
        except ImportError:
            records = _try_dataframe_records(df_or_dict, limit)
        return _ok(
            f"{len(records)} branch rows returned",
            {"count": len(records), "branches": records},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"list_branches failed: {exc}")


# ---------------------------------------------------------------------------
# Category 9: Export & graph analytics
# ---------------------------------------------------------------------------

@mcp.tool()
def export_tables(output_dir: str) -> Dict[str, Any]:
    """Export the network as per-element CSV files for spreadsheet review.

    Writes ``buses.csv``, ``branches.csv``, ``generators.csv``,
    ``loads.csv``, ``shunts.csv`` into ``output_dir``. Parallels
    PyPSA's ``export_to_csv_folder`` but uses surge-py's
    ``*_dataframe()`` accessors.

    Args:
        output_dir: Destination directory. Created if it does not exist.

    Returns:
        {"status", "message", "results": {"files": [...], "rows": {...}}}.
    """
    try:
        import csv as _csv
        import os
        net = _require_network()
        os.makedirs(output_dir, exist_ok=True)
        written: List[str] = []
        rows: Dict[str, int] = {}
        for fname, accessor in (
            ("buses.csv", "bus_dataframe"),
            ("branches.csv", "branch_dataframe"),
            ("generators.csv", "gen_dataframe"),
            ("loads.csv", "loads_dataframe"),
            ("shunts.csv", "shunts_dataframe"),
        ):
            payload = getattr(net, accessor)()
            path = os.path.join(output_dir, fname)
            # Pandas path: real DataFrame with to_csv
            if hasattr(payload, "to_csv"):
                payload.to_csv(path, index=True)
                n_rows = int(payload.shape[0])
            else:
                # Dict-of-columns fallback (pandas not installed)
                columns = list(payload.keys())
                cols_data = [list(payload[c]) for c in columns]
                n_rows = len(cols_data[0]) if cols_data else 0
                with open(path, "w", newline="") as f:
                    w = _csv.writer(f)
                    w.writerow(columns)
                    for i in range(n_rows):
                        w.writerow([cols_data[j][i] for j in range(len(columns))])
            written.append(path)
            rows[fname] = n_rows
        return _ok(
            f"{len(written)} CSV files written to {output_dir}",
            {"files": written, "rows": rows},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"export_tables failed: {exc}")


@mcp.tool()
def get_topology(
    as_networkx: bool = False,
    in_service_only: bool = True,
) -> Dict[str, Any]:
    """Return the network topology as nodes + edges.

    Use for graph reasoning: radial detection, path construction for
    ATC source/sink setup, reasoning about islands after contingencies.

    Args:
        as_networkx: If True, also return a ``networkx_repr`` payload
            that can be fed directly to ``networkx.from_dict_of_lists``.
        in_service_only: If True (default), exclude out-of-service
            branches from edges.

    Returns:
        {"status", "message", "results": {
            "nodes": [bus_number, ...],
            "edges": [{"from": int, "to": int, "circuit": int,
                       "is_transformer": bool, "in_service": bool},
                      ...],
            "networkx_repr": {bus: [neighbor, ...], ...}  # if as_networkx
        }}.
    """
    try:
        net = _require_network()
        nodes = list(net.bus_numbers)
        branches = net.in_service_branches if in_service_only else net.branches
        edges = [
            {
                "from": int(b.from_bus),
                "to": int(b.to_bus),
                "circuit": int(b.circuit),
                "is_transformer": bool(b.is_transformer),
                "in_service": bool(b.in_service),
            }
            for b in branches
        ]
        out: Dict[str, Any] = {"nodes": nodes, "edges": edges}
        if as_networkx:
            adj: Dict[int, List[int]] = {bn: [] for bn in nodes}
            for e in edges:
                adj.setdefault(e["from"], []).append(e["to"])
                adj.setdefault(e["to"], []).append(e["from"])
            out["networkx_repr"] = adj
        return _ok(
            f"{len(nodes)} nodes, {len(edges)} edges",
            out,
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"get_topology failed: {exc}")


@mcp.tool()
def find_path(
    from_bus: int,
    to_bus: int,
    in_service_only: bool = True,
) -> Dict[str, Any]:
    """Find the shortest (fewest-branch) path between two buses (BFS).

    Useful for constructing transfer paths, verifying connectivity, or
    inspecting what sits between a source and a sink. Does not weight
    by impedance — for electrical distance use ``compute_ptdf``.

    Args:
        from_bus: Source bus number.
        to_bus: Target bus number.
        in_service_only: If True, only traverse in-service branches.

    Returns:
        {"status", "message", "results": {
            "path": [bus, bus, ...] | None,
            "length": int,   # number of hops; 0 means not connected
            "connected": bool,
        }}.
    """
    try:
        from collections import deque
        net = _require_network()
        branches = net.in_service_branches if in_service_only else net.branches
        adj: Dict[int, List[int]] = {}
        for b in branches:
            adj.setdefault(int(b.from_bus), []).append(int(b.to_bus))
            adj.setdefault(int(b.to_bus), []).append(int(b.from_bus))
        if from_bus == to_bus:
            return _ok("same bus", {"path": [from_bus], "length": 0, "connected": True})
        seen = {from_bus}
        q: deque = deque([(from_bus, [from_bus])])
        while q:
            node, path = q.popleft()
            for nbr in adj.get(node, []):
                if nbr == to_bus:
                    full = path + [nbr]
                    return _ok(
                        f"path of length {len(full) - 1} found",
                        {"path": full, "length": len(full) - 1, "connected": True},
                    )
                if nbr not in seen:
                    seen.add(nbr)
                    q.append((nbr, path + [nbr]))
        return _ok(
            f"no path from bus {from_bus} to bus {to_bus}",
            {"path": None, "length": 0, "connected": False},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"find_path failed: {exc}")


@mcp.tool()
def get_islands() -> Dict[str, Any]:
    """Return the connected islands of the network (by bus number).

    After a contingency that splits the network, use this to see which
    buses are still connected together. Each island is a list of bus
    numbers.

    Returns:
        {"status", "message", "results": {
            "n_islands": int,
            "islands": [[bus, ...], ...],  # sorted largest-first
        }}.
    """
    try:
        net = _require_network()
        islands = net.islands()
        islands_sorted = sorted(islands, key=len, reverse=True)
        return _ok(
            f"{len(islands_sorted)} island(s)",
            {
                "n_islands": len(islands_sorted),
                "islands": [list(i) for i in islands_sorted],
            },
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"get_islands failed: {exc}")


@mcp.tool()
def get_dispatch_request_schema() -> Dict[str, Any]:
    """Return the JSON schema for the ``request`` argument of ``run_sced`` / ``run_scuc``.

    The SCUC / SCED ``request`` is a complex nested dict (periods,
    commitment policy, reserve zones, price caps, etc). Call this tool
    *before* constructing a request to see the exact expected shape
    rather than guessing. The schema is generated from Rust
    ``surge_dispatch::DispatchRequest`` via ``schemars``.

    Returns:
        {"status", "message", "results": <JSON schema>}.
    """
    try:
        import json
        from pathlib import Path
        here = Path(__file__).resolve()
        candidates = [
            # Sibling in PowerMCP/surge/ (if user dropped a copy in)
            here.parent / "DISPATCH_REQUEST_SCHEMA.json",
            # Co-located PowerSkills checkout: .../Power-Agent/{PowerMCP,PowerSkills}/surge/
            here.parent.parent.parent / "PowerSkills/surge/references/DISPATCH_REQUEST_SCHEMA.json",
        ]
        schema_file = next((p for p in candidates if p.exists()), None)
        if schema_file is None:
            return _err(
                "DISPATCH_REQUEST_SCHEMA.json not found — expected in "
                "PowerSkills/surge/references/ or alongside surge_mcp.py. "
                f"Searched: {[str(p) for p in candidates]}"
            )
        schema = json.loads(schema_file.read_text())
        return _ok(
            f"DispatchRequest schema ({schema_file.stat().st_size} bytes)",
            schema,
        )
    except Exception as exc:
        return _err(f"get_dispatch_request_schema failed: {exc}")


# ---------------------------------------------------------------------------
# Category 10: Network construction & editing
# ---------------------------------------------------------------------------

@mcp.tool()
def create_empty_network(
    name: str = "",
    base_mva: float = 100.0,
    freq_hz: float = 60.0,
) -> Dict[str, Any]:
    """Create a new empty network and make it the active network.

    Use this to build a synthetic case from scratch, or as a starting
    point before ``add_bus`` / ``add_generator`` / ``add_line`` calls.

    Args:
        name: Optional network name.
        base_mva: System base MVA (default 100).
        freq_hz: Nominal frequency (default 60).

    Returns:
        {"status", "message", "results": <empty network summary>}.
    """
    global _current_net, _last_pf_result
    try:
        _current_net = surge.Network(name=name, base_mva=base_mva, freq_hz=freq_hz)
        _last_pf_result = None
        return _ok(
            f"empty network created (base_mva={base_mva}, freq_hz={freq_hz})",
            _current_net.summary(),
        )
    except Exception as exc:
        return _err(f"create_empty_network failed: {exc}")


@mcp.tool()
def add_bus(
    number: int,
    bus_type: str,
    base_kv: float,
    name: str = "",
    pd_mw: float = 0.0,
    qd_mvar: float = 0.0,
    vm_pu: float = 1.0,
    va_deg: float = 0.0,
) -> Dict[str, Any]:
    """Add a bus to the active network.

    Args:
        number: External bus number (must be unique).
        bus_type: One of ``"PQ"``, ``"PV"``, ``"Slack"``, ``"Isolated"``.
        base_kv: Nominal voltage (kV).
        name: Optional bus name.
        pd_mw: Active power demand (MW).
        qd_mvar: Reactive power demand (MVAr).
        vm_pu: Initial voltage magnitude (p.u.).
        va_deg: Initial voltage angle (degrees).

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.add_bus(
            number, bus_type, base_kv,
            name=name, pd_mw=pd_mw, qd_mvar=qd_mvar,
            vm_pu=vm_pu, va_deg=va_deg,
        )
        return _ok(f"bus {number} added ({bus_type}, {base_kv} kV)")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_bus failed: {exc}")


@mcp.tool()
def add_generator(
    bus: int,
    p_mw: float,
    pmax_mw: float,
    pmin_mw: float = 0.0,
    vs_pu: float = 1.0,
    qmax_mvar: float = 9999.0,
    qmin_mvar: float = -9999.0,
    machine_id: str = "1",
    id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a generator at a bus.

    Args:
        bus: Bus number.
        p_mw: Real power output (MW).
        pmax_mw: Maximum real power (MW).
        pmin_mw: Minimum real power (MW).
        vs_pu: Voltage setpoint (p.u.).
        qmax_mvar: Maximum reactive power (MVAr).
        qmin_mvar: Minimum reactive power (MVAr).
        machine_id: PSS/E machine id (preserved as metadata).
        id: Canonical generator id. Auto-assigned when omitted.

    Returns:
        {"status", "message", "results": {"id": <canonical id>}}.
    """
    try:
        net = _require_network()
        gen_id = net.add_generator(
            bus, p_mw, pmax_mw,
            pmin_mw=pmin_mw, vs_pu=vs_pu,
            qmax_mvar=qmax_mvar, qmin_mvar=qmin_mvar,
            machine_id=machine_id, id=id,
        )
        return _ok(
            f"generator added at bus {bus} (id={gen_id}, p={p_mw} MW)",
            {"id": gen_id},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_generator failed: {exc}")


@mcp.tool()
def add_load(
    bus: int,
    pd_mw: float,
    qd_mvar: float,
    load_id: str = "1",
    conforming: bool = True,
) -> Dict[str, Any]:
    """Add a discrete load record at a bus.

    Multiple loads may share the same bus; they are distinguished by
    ``load_id``.

    Args:
        bus: Bus number.
        pd_mw: Real power demand (MW).
        qd_mvar: Reactive power demand (MVAr).
        load_id: Load identifier string (default ``"1"``).
        conforming: Whether the load scales with the area forecast.

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.add_load(bus, pd_mw, qd_mvar, load_id=load_id, conforming=conforming)
        return _ok(f"load added at bus {bus} ({pd_mw} MW / {qd_mvar} MVAr, id={load_id})")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_load failed: {exc}")


@mcp.tool()
def add_line(
    from_bus: int,
    to_bus: int,
    r_ohm_per_km: float,
    x_ohm_per_km: float,
    b_us_per_km: float,
    length_km: float,
    base_kv: float,
    rate_a_mva: float = 0.0,
    circuit: int = 1,
) -> Dict[str, Any]:
    """Add a transmission line from physical parameters.

    Surge converts Ω/km and µS/km to per-unit internally using
    ``z_base = base_kv² / base_mva``.

    Args:
        from_bus: From-bus number.
        to_bus: To-bus number.
        r_ohm_per_km: Series resistance (Ω/km).
        x_ohm_per_km: Series reactance (Ω/km).
        b_us_per_km: Shunt susceptance (µS/km).
        length_km: Line length in km.
        base_kv: Nominal voltage (kV) for per-unit conversion.
        rate_a_mva: Thermal limit (MVA). 0 = unconstrained.
        circuit: Circuit id for parallel lines (default 1).

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.add_line(
            from_bus, to_bus,
            r_ohm_per_km, x_ohm_per_km, b_us_per_km,
            length_km, base_kv,
            rate_a_mva=rate_a_mva, circuit=circuit,
        )
        return _ok(
            f"line added ({from_bus}->{to_bus} ckt {circuit}, {length_km} km, "
            f"{base_kv} kV, rate_a={rate_a_mva} MVA)"
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_line failed: {exc}")


@mcp.tool()
def add_transformer(
    from_bus: int,
    to_bus: int,
    mva_rating: float,
    v1_kv: float,
    v2_kv: float,
    z_percent: float,
    r_percent: float = 0.5,
    tap_pu: float = 1.0,
    shift_deg: float = 0.0,
    rate_a_mva: float = 0.0,
    circuit: int = 1,
) -> Dict[str, Any]:
    """Add a transformer from nameplate parameters.

    Percent impedance on the transformer's MVA base is converted to
    per-unit on the system base.

    Args:
        from_bus: HV (primary) bus number.
        to_bus: LV (secondary) bus number.
        mva_rating: Transformer MVA rating.
        v1_kv: Primary rated voltage (kV).
        v2_kv: Secondary rated voltage (kV).
        z_percent: Impedance on transformer MVA base (e.g. 8.0 for 8%).
        r_percent: Resistance on transformer MVA base.
        tap_pu: Off-nominal tap ratio (p.u.).
        shift_deg: Phase shift angle (degrees).
        rate_a_mva: Thermal rating (MVA). 0 = use mva_rating.
        circuit: Circuit id (default 1).

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.add_transformer(
            from_bus, to_bus, mva_rating, v1_kv, v2_kv, z_percent,
            r_percent=r_percent, tap_pu=tap_pu, shift_deg=shift_deg,
            rate_a_mva=rate_a_mva, circuit=circuit,
        )
        return _ok(
            f"transformer added ({from_bus}->{to_bus} ckt {circuit}, "
            f"{mva_rating} MVA, {v1_kv}/{v2_kv} kV, z={z_percent}%)"
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_transformer failed: {exc}")


@mcp.tool()
def add_storage(
    bus: int,
    charge_mw_max: float,
    discharge_mw_max: float,
    energy_capacity_mwh: float,
    efficiency: float = 0.9,
    soc_initial_mwh: Optional[float] = None,
    machine_id: str = "1",
    id: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a storage resource (BESS / pumped hydro) as a bidirectional generator.

    Surge models storage as a generator with ``pmin = -charge_mw_max``
    (charging) and ``pmax = discharge_mw_max`` (discharging), with
    ``StorageParams`` attached for SOC bookkeeping.

    Args:
        bus: Bus number.
        charge_mw_max: Maximum charge rate (MW, positive).
        discharge_mw_max: Maximum discharge rate (MW, positive).
        energy_capacity_mwh: Energy capacity (MWh).
        efficiency: Round-trip efficiency in (0, 1].
        soc_initial_mwh: Initial SOC (MWh). Defaults to half capacity.
        machine_id: PSS/E machine id.
        id: Canonical generator id. Auto-assigned when omitted.

    Returns:
        {"status", "message", "results": {"id": <canonical id>}}.
    """
    try:
        net = _require_network()
        soc0 = soc_initial_mwh if soc_initial_mwh is not None else energy_capacity_mwh / 2.0
        params = surge.StorageParams(
            energy_capacity_mwh=energy_capacity_mwh,
            efficiency=efficiency,
            soc_initial_mwh=soc0,
            soc_max_mwh=energy_capacity_mwh,
        )
        gen_id = net.add_storage(
            bus, charge_mw_max, discharge_mw_max, params,
            machine_id=machine_id, id=id,
        )
        return _ok(
            f"storage added at bus {bus} (id={gen_id}, "
            f"±{discharge_mw_max}/{charge_mw_max} MW, {energy_capacity_mwh} MWh)",
            {"id": gen_id},
        )
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"add_storage failed: {exc}")


@mcp.tool()
def remove_bus(number: int) -> Dict[str, Any]:
    """Remove a bus and everything connected to it (branches, generators, loads)."""
    try:
        net = _require_network()
        net.remove_bus(number)
        return _ok(f"bus {number} and connected elements removed")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"remove_bus failed: {exc}")


@mcp.tool()
def remove_branch(from_bus: int, to_bus: int, circuit: int = 1) -> Dict[str, Any]:
    """Remove a branch (line or transformer) by (from, to, circuit)."""
    try:
        net = _require_network()
        net.remove_branch(from_bus, to_bus, circuit)
        return _ok(f"branch {from_bus}->{to_bus} ckt {circuit} removed")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"remove_branch failed: {exc}")


@mcp.tool()
def remove_generator(id: str) -> Dict[str, Any]:
    """Remove a generator by canonical id (e.g. ``gen_1_1``)."""
    try:
        net = _require_network()
        net.remove_generator(id)
        return _ok(f"generator {id} removed")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"remove_generator failed: {exc}")


@mcp.tool()
def remove_load(bus: int, load_id: str = "1") -> Dict[str, Any]:
    """Remove the first load matching ``(bus, load_id)``."""
    try:
        net = _require_network()
        net.remove_load(bus, load_id)
        return _ok(f"load at bus {bus} (id={load_id}) removed")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"remove_load failed: {exc}")


@mcp.tool()
def set_branch_rating(
    from_bus: int,
    to_bus: int,
    rate_a_mva: float,
    circuit: int = 1,
) -> Dict[str, Any]:
    """Set the long-term thermal rating of a branch (MVA)."""
    try:
        net = _require_network()
        net.set_branch_rating(from_bus, to_bus, rate_a_mva, circuit)
        return _ok(f"branch {from_bus}->{to_bus} ckt {circuit} rate_a set to {rate_a_mva} MVA")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"set_branch_rating failed: {exc}")


@mcp.tool()
def set_branch_in_service(
    from_bus: int,
    to_bus: int,
    in_service: bool,
    circuit: int = 1,
) -> Dict[str, Any]:
    """Set a branch in- or out-of-service (outage simulation)."""
    try:
        net = _require_network()
        net.set_branch_in_service(from_bus, to_bus, in_service, circuit)
        state = "in service" if in_service else "out of service"
        return _ok(f"branch {from_bus}->{to_bus} ckt {circuit} set {state}")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"set_branch_in_service failed: {exc}")


@mcp.tool()
def set_generator_limits(id: str, pmax_mw: float, pmin_mw: float) -> Dict[str, Any]:
    """Set the real power limits (MW) of a generator."""
    try:
        net = _require_network()
        net.set_generator_limits(id, pmax_mw, pmin_mw)
        return _ok(f"generator {id} limits set to [{pmin_mw}, {pmax_mw}] MW")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"set_generator_limits failed: {exc}")


@mcp.tool()
def set_generator_in_service(id: str, in_service: bool) -> Dict[str, Any]:
    """Set the in-service status of a generator."""
    try:
        net = _require_network()
        net.set_generator_in_service(id, in_service)
        state = "in service" if in_service else "out of service"
        return _ok(f"generator {id} set {state}")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"set_generator_in_service failed: {exc}")


@mcp.tool()
def scale_loads(factor: float, area: Optional[int] = None) -> Dict[str, Any]:
    """Multiply every Load's demand by ``factor`` (optionally restricted to one area).

    Args:
        factor: Multiplicative scale (e.g. 1.1 for +10% demand).
        area: If given, scale only loads whose bus is in this area number.

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.scale_loads(factor, area) if area is not None else net.scale_loads(factor)
        scope = f" in area {area}" if area is not None else ""
        return _ok(f"loads scaled by {factor}{scope}")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"scale_loads failed: {exc}")


@mcp.tool()
def scale_generators(factor: float, area: Optional[int] = None) -> Dict[str, Any]:
    """Multiply every in-service generator's dispatch by ``factor``.

    Args:
        factor: Multiplicative scale.
        area: If given, scale only generators whose bus is in this area number.

    Returns:
        {"status", "message"}.
    """
    try:
        net = _require_network()
        net.scale_generators(factor, area) if area is not None else net.scale_generators(factor)
        scope = f" in area {area}" if area is not None else ""
        return _ok(f"generators scaled by {factor}{scope}")
    except RuntimeError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(f"scale_generators failed: {exc}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
