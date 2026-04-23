#!/usr/bin/env python3
"""Integration tests for the Surge MCP server.

Eight groups:
  1. Solver matrix — DC/AC-OPF, SCOPF, SCED across solver selections.
  2. Format I/O round-trip — save + reload for each supported extension.
  3. MCP stdio transport — subprocess, real JSON-RPC via the MCP SDK.
  4. Power flow — AC, DC, FDPF convergence + non-convergence path.
  5. DC sensitivities — PTDF / LODF / OTDF format variants and guards.
  6. Contingency + transfer — N-1 branch / generator, NERC ATC, SCUC.
  7. Construction lifecycle — build → solve → edit → scale → remove.
  8. Export + graph — CSV export (with and without pandas), topology,
     path, islands, dispatch schema, inspection.

Run:
    python test_integration.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

MCP_PATH = Path(__file__).resolve().parent / "surge_mcp.py"


# ---------------------------------------------------------------------------
# Helpers — load the MCP module and call its tools directly.
# ---------------------------------------------------------------------------


def _load_mcp_module():
    spec = importlib.util.spec_from_file_location("surge_mcp", str(MCP_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _call(mod, tool_name: str, **kwargs) -> Dict[str, Any]:
    tool = mod.mcp._tool_manager._tools[tool_name]
    return tool.fn(**kwargs)


# ---------------------------------------------------------------------------
# Test 1: Solver matrix
# ---------------------------------------------------------------------------


def test_solver_matrix() -> Tuple[int, int]:
    """Run each OPF tool with each accepted solver value; confirm all work.

    Returns (passed, total).
    """
    print("\n" + "=" * 70)
    print("TEST 1 — Solver matrix")
    print("=" * 70)

    mod = _load_mcp_module()

    # Probe for optional commercial solvers. We only report these if present;
    # they are NOT required for the matrix to pass.
    import os
    optional_solvers = {
        "gurobi": bool(os.environ.get("GUROBI_HOME")),
        "copt": bool(os.environ.get("COPT_HOME")),
        "cplex": bool(os.environ.get("CPLEX_HOME")),
    }
    print("  Optional solvers detected (by env var):", optional_solvers)

    # Load case118 once.
    r = _call(mod, "load_builtin_case", name="case118")
    assert r["status"] == "success", r

    passed = 0
    total = 0

    # --- DC-OPF ---
    dc_solvers = ["default", "highs"] + [
        s for s, present in optional_solvers.items() if present
    ]
    dc_costs: List[float] = []
    for solver in dc_solvers:
        total += 1
        res = _call(mod, "run_dc_opf", lp_solver=solver)
        if res["status"] != "success":
            print(f"  FAIL DC-OPF lp_solver={solver}: {res['message']}")
            continue
        cost = res["results"]["total_cost"]
        dc_costs.append(cost)
        print(f"  OK   DC-OPF lp_solver={solver:<10s}  cost={cost:.2f}")
        passed += 1
    # All DC-OPF solvers on the same LP should land at the same cost
    # (within 0.1% — HiGHS vs Gurobi can differ slightly at tolerances).
    if len(dc_costs) >= 2:
        spread = max(dc_costs) - min(dc_costs)
        avg = sum(dc_costs) / len(dc_costs)
        if avg > 0 and spread / avg > 1e-3:
            total += 1
            print(
                f"  FAIL DC-OPF solver-consistency: spread={spread:.2f} "
                f"({spread / avg * 100:.3f}% of avg)"
            )
        else:
            total += 1
            passed += 1
            print(
                f"  OK   DC-OPF solver-consistency: "
                f"spread={spread:.2f} ({spread / avg * 100:.4f}% of avg)"
            )

    # --- AC-OPF ---
    # Ipopt is the open-source NLP default; no commercial equivalents are
    # ambient in most envs, so we run default + explicit ipopt.
    for solver in ["default", "ipopt"]:
        total += 1
        res = _call(mod, "run_ac_opf", nlp_solver=solver)
        if res["status"] != "success":
            print(f"  FAIL AC-OPF nlp_solver={solver}: {res['message']}")
            continue
        cost = res["results"]["total_cost"]
        print(f"  OK   AC-OPF nlp_solver={solver:<10s}  cost={cost:.2f}")
        passed += 1

    # --- SCOPF ---
    total += 1
    res = _call(mod, "run_scopf", lp_solver="highs", nlp_solver="ipopt")
    if res["status"] == "success":
        print(
            f"  OK   SCOPF   lp=highs, nlp=ipopt  "
            f"converged={res['results']['converged']}, "
            f"iterations={res['results']['iterations']}"
        )
        passed += 1
    else:
        print(f"  FAIL SCOPF: {res['message']}")

    # --- SCUC via run_sced (with HiGHS default) ---
    # Use the market30 case which is built for dispatch.
    _call(mod, "load_builtin_case", name="market30")
    total += 1
    res = _call(mod, "run_sced", lp_solver="highs")
    if res["status"] == "success":
        print("  OK   SCED    lp_solver=highs on market30")
        passed += 1
    else:
        print(f"  FAIL SCED on market30 with HiGHS: {res['message']}")

    print(f"\n  Solver matrix: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 2: Format I/O round-trip
# ---------------------------------------------------------------------------


def test_format_roundtrip() -> Tuple[int, int]:
    """Save and reload in every supported extension; compare summaries.

    Core counts must survive the round-trip for a round-trip to count
    as a pass. Format-specific lossy behavior (e.g. PSS/E losing some
    surge-JSON-native metadata) is accepted as long as bus / branch /
    generator counts match.
    """
    print("\n" + "=" * 70)
    print("TEST 2 — Format I/O round-trip")
    print("=" * 70)

    mod = _load_mcp_module()

    # Anchor on case118.
    _call(mod, "load_builtin_case", name="case118")
    original = _call(mod, "get_network_info")["results"]
    anchor = {
        k: original[k]
        for k in ("n_buses", "n_branches", "n_generators", "n_loads")
    }
    print(f"  Anchor summary (case118): {anchor}")

    # Each tuple is (extension, human name). The server auto-detects the
    # format from the extension.
    formats = [
        ("surge.json.zst", "Surge JSON (zst)"),
        ("surge.json", "Surge JSON (plain)"),
        ("m", "MATPOWER"),
        ("raw", "PSS/E RAW"),
        ("xiidm", "XIIDM"),
    ]

    passed = 0
    total = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        for ext, label in formats:
            total += 1
            fname = Path(tmpdir) / f"case118.{ext}"
            # Re-load original, save, clear, reload.
            _call(mod, "load_builtin_case", name="case118")
            save_res = _call(mod, "save_network", file_path=str(fname))
            if save_res["status"] != "success":
                print(f"  FAIL {label:<24s} save: {save_res['message']}")
                continue
            if not fname.exists():
                print(f"  FAIL {label:<24s} save reported success but file missing")
                continue

            load_res = _call(mod, "load_network", file_path=str(fname))
            if load_res["status"] != "success":
                print(f"  FAIL {label:<24s} reload: {load_res['message']}")
                continue

            reloaded = _call(mod, "get_network_info")["results"]
            check = {k: reloaded[k] for k in anchor}
            if check == anchor:
                size_kb = fname.stat().st_size / 1024
                print(
                    f"  OK   {label:<24s} round-trip preserves counts "
                    f"({size_kb:>7.1f} KB on disk)"
                )
                passed += 1
            else:
                print(
                    f"  FAIL {label:<24s} round-trip counts mismatch: "
                    f"{check} != {anchor}"
                )

    print(f"\n  Format round-trips: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 3: MCP stdio transport
# ---------------------------------------------------------------------------


async def _mcp_stdio_round_trip() -> Tuple[int, int]:
    """Launch surge_mcp.py as a subprocess and drive it over stdio.

    Validates:
      - Server starts and responds to initialize.
      - The tool list reports all 44 tools.
      - A representative tool call (load_builtin_case → get_network_info)
        returns a success-shaped payload through the real MCP protocol.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_PATH)],
    )

    passed = 0
    total = 0

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            total += 1
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            if len(names) == 44:
                print(f"  OK   server advertises 44 tools via MCP protocol")
                passed += 1
            else:
                print(
                    f"  FAIL server advertised {len(names)} tools, expected 44"
                )
                print(f"       advertised: {names}")

            # Exercise a round-trip through the protocol.
            total += 1
            result = await session.call_tool(
                "load_builtin_case", {"name": "case118"}
            )
            payload = _parse_tool_result(result)
            if payload and payload.get("status") == "success":
                summary = payload.get("results", {}).get("summary", {})
                print(
                    f"  OK   MCP call_tool('load_builtin_case', name='case118') "
                    f"→ n_buses={summary.get('n_buses')}"
                )
                passed += 1
            else:
                print(f"  FAIL MCP call_tool('load_builtin_case'): {payload}")

            total += 1
            result = await session.call_tool("get_network_info", {})
            payload = _parse_tool_result(result)
            if payload and payload.get("status") == "success":
                res = payload.get("results", {})
                print(
                    f"  OK   MCP call_tool('get_network_info') "
                    f"→ n_branches={res.get('n_branches')}, "
                    f"voltage_levels={res.get('voltage_levels_kv')}"
                )
                passed += 1
            else:
                print(f"  FAIL MCP call_tool('get_network_info'): {payload}")

            # Exercise an error path to confirm error responses also
            # make it through the transport intact.
            total += 1
            result = await session.call_tool(
                "load_builtin_case", {"name": "not-a-real-case"}
            )
            payload = _parse_tool_result(result)
            if payload and payload.get("status") == "error":
                print(
                    f"  OK   MCP error path round-trips: "
                    f"'{payload['message'][:60]}...'"
                )
                passed += 1
            else:
                print(
                    f"  FAIL MCP error path: expected status=error, got {payload}"
                )

    return passed, total


def _parse_tool_result(result) -> Optional[Dict[str, Any]]:
    """Extract the payload dict from an MCP call_tool response."""
    if not getattr(result, "content", None):
        return None
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"status": "error", "message": text}
    return None


def test_mcp_stdio() -> Tuple[int, int]:
    print("\n" + "=" * 70)
    print("TEST 3 — MCP stdio transport")
    print("=" * 70)
    passed, total = asyncio.run(_mcp_stdio_round_trip())
    print(f"\n  MCP stdio: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 4: Power flow
# ---------------------------------------------------------------------------


def test_power_flow() -> Tuple[int, int]:
    """Exercise AC / DC / FDPF on a well-behaved case + a case that should
    fail to converge."""
    print("\n" + "=" * 70)
    print("TEST 4 — Power flow")
    print("=" * 70)

    mod = _load_mcp_module()
    passed = 0
    total = 0

    _call(mod, "load_builtin_case", name="case118")

    # AC PF
    total += 1
    res = _call(mod, "run_ac_power_flow")
    if (
        res["status"] == "success"
        and res["results"]["converged"]
        and res["results"]["max_mismatch"] < 1e-6
    ):
        print(
            f"  OK   AC PF case118        iterations={res['results']['iterations']}, "
            f"max_mismatch={res['results']['max_mismatch']:.2e}"
        )
        passed += 1
    else:
        print(f"  FAIL AC PF case118: {res}")

    # DC PF
    total += 1
    res = _call(mod, "run_dc_power_flow")
    if res["status"] == "success":
        print("  OK   DC PF case118")
        passed += 1
    else:
        print(f"  FAIL DC PF case118: {res['message']}")

    # FDPF
    total += 1
    res = _call(mod, "run_fast_decoupled_pf", variant="xb")
    if res["status"] == "success":
        print(
            f"  OK   FDPF xb case118      iterations={res['results']['iterations']}"
        )
        passed += 1
    else:
        print(f"  FAIL FDPF xb case118: {res['message']}")

    # Non-convergent case: over-stress case9 so AC PF can't find a solution.
    _call(mod, "load_builtin_case", name="case9")
    _call(mod, "scale_loads", factor=5.0)
    total += 1
    res = _call(mod, "run_ac_power_flow", max_iterations=10, tolerance=1e-8)
    if res["status"] == "success" and not res["results"]["converged"]:
        print("  OK   AC PF non-convergence path reports converged=False")
        passed += 1
    else:
        print(f"  FAIL AC PF non-convergence path: {res}")

    print(f"\n  Power flow: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 5: Sensitivities
# ---------------------------------------------------------------------------


def test_sensitivities() -> Tuple[int, int]:
    """Exercise PTDF / LODF / OTDF across formats and verify guard rails."""
    print("\n" + "=" * 70)
    print("TEST 5 — DC sensitivities")
    print("=" * 70)

    mod = _load_mcp_module()
    passed = 0
    total = 0

    _call(mod, "load_builtin_case", name="case118")

    # PTDF summary + top_k truncation
    total += 1
    res = _call(mod, "compute_ptdf", format="summary", top_k_per_branch=5)
    results = res.get("results", {}) if res["status"] == "success" else {}
    top_per_row = results.get("top_per_row") or results.get("top_k") or []
    if (
        res["status"] == "success"
        and top_per_row
        and all(len(row) <= 5 for row in top_per_row)
    ):
        print(f"  OK   PTDF summary top_k=5 truncates ({len(top_per_row)} rows)")
        passed += 1
    else:
        print(f"  FAIL PTDF summary top_k=5: {res.get('message') or results.keys()}")

    # PTDF sparse
    total += 1
    res = _call(mod, "compute_ptdf", format="sparse")
    if res["status"] == "success" and "indptr" in res["results"]:
        print(f"  OK   PTDF sparse CSR      nnz={len(res['results'].get('data', []))}")
        passed += 1
    else:
        print(f"  FAIL PTDF sparse: {res.get('message') or list(res.get('results', {}).keys())}")

    # LODF summary
    total += 1
    res = _call(mod, "compute_lodf", format="summary", top_k_per_branch=3)
    if res["status"] == "success" and res["results"].get("shape"):
        print(f"  OK   LODF summary         shape={tuple(res['results']['shape'])}")
        passed += 1
    else:
        print(f"  FAIL LODF summary: {res.get('message') or list(res.get('results', {}).keys())}")

    # OTDF summary with a bounded outage × monitored pair
    total += 1
    outages = [(8, 9, 1)]
    monitored = [(4, 5, 1), (5, 6, 1)]
    res = _call(
        mod,
        "compute_otdf",
        outage_branches=outages,
        monitored_branches=monitored,
        format="summary",
        top_k_per_pair=3,
    )
    if res["status"] == "success":
        print(f"  OK   OTDF summary         {len(outages)}×{len(monitored)} pairs")
        passed += 1
    else:
        print(f"  FAIL OTDF summary: {res['message']}")

    # OTDF full refusal — protects against unintentional 3-D tensor dumps
    total += 1
    res = _call(
        mod,
        "compute_otdf",
        outage_branches=outages,
        monitored_branches=monitored,
        format="full",
    )
    if res["status"] == "error":
        print("  OK   OTDF format=\"full\" is refused (dense tensor guard)")
        passed += 1
    else:
        print("  FAIL OTDF format=\"full\" should error but did not")

    print(f"\n  Sensitivities: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 6: Contingency + transfer capability
# ---------------------------------------------------------------------------


def test_contingency_transfer() -> Tuple[int, int]:
    """N-1 analysis against a stressed case + NERC ATC between two areas."""
    print("\n" + "=" * 70)
    print("TEST 6 — Contingency + transfer")
    print("=" * 70)

    mod = _load_mcp_module()
    passed = 0
    total = 0

    # Stress case9 so every N-1 contingency produces violations.
    _call(mod, "load_builtin_case", name="case9")
    _call(mod, "scale_loads", factor=2.0)

    total += 1
    res = _call(mod, "run_n1_branch_contingency")
    if (
        res["status"] == "success"
        and res["results"]["n_contingencies"] >= 1
        and res["results"]["n_with_violations"] >= 1
    ):
        r = res["results"]
        print(
            f"  OK   N-1 branch stressed   {r['n_contingencies']} scenarios, "
            f"{r['n_with_violations']} with violations ({r['n_violations']} total)"
        )
        passed += 1
    else:
        print(f"  FAIL N-1 branch on stressed case9: {res}")

    total += 1
    res = _call(mod, "run_n1_generator_contingency")
    if res["status"] == "success":
        print(f"  OK   N-1 generator        {res['results']['n_contingencies']} scenarios")
        passed += 1
    else:
        print(f"  FAIL N-1 generator: {res['message']}")

    # NERC ATC between two bus groups on case118.
    _call(mod, "load_builtin_case", name="case118")
    total += 1
    res = _call(
        mod,
        "compute_nerc_atc",
        source_buses=[89, 90, 100, 103],
        sink_buses=[1, 2, 3, 12],
        name="south-north",
        trm_fraction=0.05,
    )
    if res["status"] == "success" and "atc_mw" in res["results"]:
        print(f"  OK   NERC ATC case118     atc_mw={res['results']['atc_mw']}")
        passed += 1
    else:
        print(f"  FAIL NERC ATC: {res['message']}")

    # SCUC with explicit HiGHS on market30.
    _call(mod, "load_builtin_case", name="market30")
    total += 1
    res = _call(mod, "run_scuc", lp_solver="highs")
    if res["status"] == "success":
        print("  OK   SCUC market30 HiGHS")
        passed += 1
    else:
        print(f"  FAIL SCUC market30 HiGHS: {res['message']}")

    print(f"\n  Contingency + transfer: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 7: Network construction lifecycle
# ---------------------------------------------------------------------------


def test_construction_lifecycle() -> Tuple[int, int]:
    """Build an empty network, add elements, solve, edit, scale, remove."""
    print("\n" + "=" * 70)
    print("TEST 7 — Network construction lifecycle")
    print("=" * 70)

    mod = _load_mcp_module()
    passed = 0
    total = 0

    steps: List[Tuple[str, Dict[str, Any]]] = [
        ("create_empty_network", {"name": "test", "base_mva": 100.0}),
        ("add_bus", {"number": 1, "bus_type": "Slack", "base_kv": 230.0}),
        ("add_bus", {"number": 2, "bus_type": "PV", "base_kv": 230.0}),
        ("add_bus", {"number": 3, "bus_type": "PQ", "base_kv": 138.0}),
        ("add_generator", {"bus": 1, "p_mw": 80.0, "pmax_mw": 200.0}),
        ("add_generator", {"bus": 2, "p_mw": 40.0, "pmax_mw": 150.0}),
        ("add_storage", {
            "bus": 2, "charge_mw_max": 25.0, "discharge_mw_max": 25.0,
            "energy_capacity_mwh": 50.0,
        }),
        ("add_load", {"bus": 3, "pd_mw": 80.0, "qd_mvar": 25.0}),
        ("add_line", {
            "from_bus": 1, "to_bus": 2,
            "r_ohm_per_km": 0.03, "x_ohm_per_km": 0.3, "b_us_per_km": 3.0,
            "length_km": 40.0, "base_kv": 230.0, "rate_a_mva": 300.0,
        }),
        ("add_transformer", {
            "from_bus": 2, "to_bus": 3,
            "mva_rating": 150.0, "v1_kv": 230.0, "v2_kv": 138.0,
            "z_percent": 8.0,
        }),
    ]
    for tool, args in steps:
        total += 1
        res = _call(mod, tool, **args)
        if res["status"] == "success":
            passed += 1
        else:
            print(f"  FAIL {tool}({args}): {res['message']}")

    # AC PF must converge on the synthetic case.
    total += 1
    res = _call(mod, "run_ac_power_flow")
    if res["status"] == "success" and res["results"]["converged"]:
        print(f"  OK   AC PF on synthetic 3-bus converged in {res['results']['iterations']} iter")
        passed += 1
    else:
        print(f"  FAIL AC PF on synthetic case: {res}")

    # Edits
    edits: List[Tuple[str, Dict[str, Any]]] = [
        ("set_branch_rating", {"from_bus": 1, "to_bus": 2, "rate_a_mva": 350.0}),
        ("set_branch_in_service", {"from_bus": 1, "to_bus": 2, "in_service": False}),
        ("set_branch_in_service", {"from_bus": 1, "to_bus": 2, "in_service": True}),
        ("set_generator_limits", {"id": "gen_1_1", "pmax_mw": 300.0, "pmin_mw": 10.0}),
        ("set_generator_in_service", {"id": "gen_2_1", "in_service": True}),
        ("scale_loads", {"factor": 1.1}),
        ("scale_generators", {"factor": 1.05}),
    ]
    for tool, args in edits:
        total += 1
        res = _call(mod, tool, **args)
        if res["status"] == "success":
            passed += 1
        else:
            print(f"  FAIL {tool}({args}): {res['message']}")

    # Removes + final shape check.
    removes: List[Tuple[str, Dict[str, Any]]] = [
        ("remove_load", {"bus": 3, "load_id": "1"}),
        ("remove_generator", {"id": "gen_2_2"}),  # the storage
        ("remove_branch", {"from_bus": 2, "to_bus": 3}),
        ("remove_bus", {"number": 3}),
    ]
    for tool, args in removes:
        total += 1
        res = _call(mod, tool, **args)
        if res["status"] == "success":
            passed += 1
        else:
            print(f"  FAIL {tool}({args}): {res['message']}")

    total += 1
    res = _call(mod, "get_network_info")
    info = res.get("results", {})
    if (
        res["status"] == "success"
        and info.get("n_buses") == 2
        and info.get("n_loads") == 0
    ):
        print(f"  OK   final network        n_buses=2, n_branches={info['n_branches']}")
        passed += 1
    else:
        print(f"  FAIL final shape: {info}")

    print(f"\n  Construction lifecycle: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Test 8: Export + graph analytics
# ---------------------------------------------------------------------------


def _export_tables_without_pandas(csv_dir: Path) -> bool:
    """Run export_tables in a subprocess with pandas blocked at import time.

    Returns True if all five CSVs were written and non-empty.
    """
    import subprocess

    script = f"""
import sys
sys.modules['pandas'] = None  # force the dict-of-columns fallback path
sys.path.insert(0, {str(MCP_PATH.parent)!r})
import surge_mcp as m
r = m.load_builtin_case(name='case9')
assert r['status'] == 'success', r
r = m.export_tables(output_dir={str(csv_dir)!r})
assert r['status'] == 'success', r
print('OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0 or "OK" not in result.stdout:
        return False
    expected = {"buses.csv", "branches.csv", "generators.csv", "loads.csv", "shunts.csv"}
    got = {p.name for p in csv_dir.iterdir()}
    if got != expected:
        return False
    # Each file should at least have a header line.
    return all(
        (csv_dir / f).stat().st_size > 0 for f in expected
    )


def test_export_and_graph() -> Tuple[int, int]:
    """Exercise export_tables (both pandas paths), topology, path, islands, schema."""
    print("\n" + "=" * 70)
    print("TEST 8 — Export + graph analytics")
    print("=" * 70)

    mod = _load_mcp_module()
    passed = 0
    total = 0

    _call(mod, "load_builtin_case", name="case9")

    # export_tables with pandas present
    with tempfile.TemporaryDirectory() as td:
        total += 1
        res = _call(mod, "export_tables", output_dir=td)
        expected = {"buses.csv", "branches.csv", "generators.csv", "loads.csv", "shunts.csv"}
        got = {p.name for p in Path(td).iterdir()} if res["status"] == "success" else set()
        if res["status"] == "success" and got == expected:
            print("  OK   export_tables (pandas path) wrote 5 CSVs")
            passed += 1
        else:
            print(f"  FAIL export_tables (pandas): {res.get('message')} got={got}")

    # export_tables without pandas (subprocess so the blocking is clean)
    with tempfile.TemporaryDirectory() as td:
        total += 1
        if _export_tables_without_pandas(Path(td)):
            print("  OK   export_tables (no-pandas fallback) wrote 5 CSVs")
            passed += 1
        else:
            print("  FAIL export_tables (no-pandas fallback)")

    # get_topology with networkx repr
    total += 1
    res = _call(mod, "get_topology", as_networkx=True, in_service_only=True)
    r = res.get("results", {})
    if (
        res["status"] == "success"
        and len(r.get("nodes", [])) == 9
        and len(r.get("edges", [])) == 9
        and isinstance(r.get("networkx_repr"), dict)
    ):
        print(f"  OK   get_topology         {len(r['nodes'])} nodes, {len(r['edges'])} edges")
        passed += 1
    else:
        print(f"  FAIL get_topology: {res}")

    # find_path — connected
    total += 1
    res = _call(mod, "find_path", from_bus=1, to_bus=3)
    if (
        res["status"] == "success"
        and res["results"]["connected"]
        and res["results"]["path"]
        and res["results"]["path"][0] == 1
        and res["results"]["path"][-1] == 3
    ):
        print(f"  OK   find_path 1→3        path={res['results']['path']}")
        passed += 1
    else:
        print(f"  FAIL find_path 1→3: {res}")

    # find_path — disconnected
    total += 1
    res = _call(mod, "find_path", from_bus=1, to_bus=999)
    if res["status"] == "success" and not res["results"]["connected"]:
        print("  OK   find_path disconnected returns connected=False")
        passed += 1
    else:
        print(f"  FAIL find_path disconnected: {res}")

    # get_islands after 3 forced outages that split the network
    for f, t in [(8, 9), (7, 8), (4, 9)]:
        _call(mod, "set_branch_in_service", from_bus=f, to_bus=t, in_service=False)
    total += 1
    res = _call(mod, "get_islands")
    if res["status"] == "success" and res["results"]["n_islands"] >= 2:
        print(f"  OK   get_islands after outages  n_islands={res['results']['n_islands']}")
        passed += 1
    else:
        print(f"  FAIL get_islands: {res}")

    # get_dispatch_request_schema
    total += 1
    res = _call(mod, "get_dispatch_request_schema")
    props = res.get("results", {}).get("properties", {}) if res["status"] == "success" else {}
    if res["status"] == "success" and "timeline" in props and "commitment" in props:
        print(f"  OK   get_dispatch_request_schema  {len(props)} top-level props")
        passed += 1
    else:
        print(f"  FAIL get_dispatch_request_schema: {res.get('message')}")

    # list_buses with sort + limit
    _call(mod, "load_builtin_case", name="case118")
    total += 1
    res = _call(mod, "list_buses", limit=5, sort_by="pd_mw", ascending=False)
    if (
        res["status"] == "success"
        and len(res["results"].get("buses", [])) == 5
    ):
        print("  OK   list_buses limit=5 sort_by=pd_mw descending")
        passed += 1
    else:
        print(f"  FAIL list_buses: {res}")

    # list_branches with sort + limit
    total += 1
    res = _call(mod, "list_branches", limit=5, sort_by="rate_a_mva", ascending=False)
    if (
        res["status"] == "success"
        and len(res["results"].get("branches", [])) == 5
    ):
        print("  OK   list_branches limit=5 sort_by=rate_a_mva descending")
        passed += 1
    else:
        print(f"  FAIL list_branches: {res}")

    print(f"\n  Export + graph: {passed}/{total}")
    return passed, total


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    results: List[Tuple[str, int, int]] = []

    p, t = test_solver_matrix()
    results.append(("Solver matrix", p, t))
    p, t = test_format_roundtrip()
    results.append(("Format round-trip", p, t))
    p, t = test_mcp_stdio()
    results.append(("MCP stdio transport", p, t))
    p, t = test_power_flow()
    results.append(("Power flow", p, t))
    p, t = test_sensitivities()
    results.append(("DC sensitivities", p, t))
    p, t = test_contingency_transfer()
    results.append(("Contingency + transfer", p, t))
    p, t = test_construction_lifecycle()
    results.append(("Construction lifecycle", p, t))
    p, t = test_export_and_graph()
    results.append(("Export + graph", p, t))

    print("\n" + "=" * 70)
    print("Integration summary")
    print("=" * 70)
    total_p = sum(p for _, p, _ in results)
    total_t = sum(t for _, _, t in results)
    for name, p, t in results:
        print(f"  {name:<24s}  {p}/{t}")
    print(f"  {'TOTAL':<24s}  {total_p}/{total_t}")
    print("=" * 70)
    return 0 if total_p == total_t else 1


if __name__ == "__main__":
    sys.exit(main())
