"""Native Study adapter behavior and path checks."""
import asyncio
import pytest
from powermcp import tellegen


def test_apply_is_not_an_agent_operation(monkeypatch):
    async def forbidden(*args):
        pytest.fail("rejected operation reached the native process")
    monkeypatch.setattr(tellegen, "_call", forbidden)
    with pytest.raises(ValueError, match="explicit native CLI"):
        asyncio.run(tellegen.study_run("study.json", 0, {"kind": "apply"}))


def test_paths_checked_before_native_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    async def forbidden(*args):
        pytest.fail("out-of-root path reached the native process")
    monkeypatch.setattr(tellegen, "_call", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(tellegen.study_inspect(str(tmp_path.parent / "outside.json")))


@pytest.mark.parametrize("kind", ["propose", "edit_demand", "restore_base"])
def test_mutation_keeps_revision_binding_and_returns_compact_result(tmp_path, monkeypatch, kind):
    path = tmp_path / "study.json"
    path.write_text("{}")
    received = []
    async def native(args, request):
        received.append((args, request))
        return {"summary": {"id": "s", "revision": 4, "active_goal": ["g", {"request": "lower prices", "anchor_state": "a", "objective": {"large": []}}]}, "experiment": "e", "inspected_view": {"large": []}}
    monkeypatch.setattr(tellegen, "_call", native)
    operation = {"kind": kind, "state": "a", "goal": "g"}
    result = asyncio.run(tellegen.study_run(str(path), 3, operation))
    assert received == [(["study", "run", str(path), "--progress"], {"expected_revision": 3, "operation": operation})]
    assert result["revision"] == 4 and result["experiment"] == "e"
    assert "inspected_view" not in result and "objective" not in result["active_goal"]


def test_registered_tools_include_native_study_operations():
    names = {t.name for t in asyncio.run(tellegen.mcp.list_tools())}
    assert {"study_contract", "study_create", "study_inspect", "study_run", "study_import", "study_export"} <= names


def test_cancellation_requests_graceful_native_save(monkeypatch):
    async def run():
        started, terminated, saved = asyncio.Event(), asyncio.Event(), asyncio.Event()
        class Process:
            returncode = None
            async def communicate(self, data):
                started.set()
                await terminated.wait()
                saved.set()
                self.returncode = 0
                return b'{"revision":1}', b''
            def send_signal(self, value):
                terminated.set()
            def terminate(self):
                terminated.set()
            def kill(self):
                pytest.fail("cooperative cancellation must allow the completed save")
            async def wait(self):
                return self.returncode
        async def spawn(*args, **kwargs):
            return Process()
        monkeypatch.setattr(tellegen, "_binary", lambda: "tellegen")
        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(tellegen._call(["study", "run", "study.json"], {}))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert terminated.is_set() and saved.is_set()
    asyncio.run(run())


@pytest.mark.parametrize("value", [0, -1, "nan", "inf", "invalid", 86401])
def test_invalid_execution_duration_is_rejected(value, monkeypatch):
    monkeypatch.setenv("POWERMCP_TELLEGEN_TIMEOUT_SECONDS", str(value))
    with pytest.raises(ValueError, match="duration"):
        tellegen._seconds("timeout_seconds", 1800)


# ---- end to end over the fake binary --------------------------------------------

import json
import os
import time
from pathlib import Path

import powerio

FAKE = Path(__file__).parent / "data" / "fake_tellegen.py"
CASE9 = Path(__file__).parent / "data" / "case9.m"
DIST = Path(__file__).parent / "data" / "opendss" / "fourwire_linecode.dss"
UNRESOLVED = Path(__file__).parent / "data" / "opendss" / "geometry_unresolved.dss"


@pytest.fixture
def fake_binary(tmp_path, monkeypatch):
    record = tmp_path / "record.jsonl"
    monkeypatch.setenv("POWERMCP_TELLEGEN_BINARY", str(FAKE))
    monkeypatch.setenv("FAKE_TELLEGEN_RECORD", str(record))
    monkeypatch.delenv("FAKE_TELLEGEN_SLEEP", raising=False)

    def calls():
        if not record.exists():
            return []
        return [json.loads(line) for line in record.read_text().splitlines()]

    return calls


def test_registered_tools_list_solving_planning_and_studies():
    names = {t.name for t in asyncio.run(tellegen.mcp.list_tools())}
    assert names == {
        "capabilities", "contract", "solve", "solve_module", "plan",
        "study_contract", "study_create", "study_inspect", "study_run", "study_import", "study_export",
    }


def test_unconfigured_binary_names_the_configuration(monkeypatch):
    monkeypatch.delenv("POWERMCP_TELLEGEN_BINARY", raising=False)
    monkeypatch.setattr(tellegen.shutil, "which", lambda name: None)
    monkeypatch.setattr(tellegen, "get", lambda *args: None)
    with pytest.raises(RuntimeError, match="tellegen.binary"):
        tellegen._binary()


def test_capabilities_and_contract_over_the_fake_binary(fake_binary):
    caps = asyncio.run(tellegen.capabilities())
    assert caps["binary"].endswith("fake_tellegen.py")
    assert caps["capabilities"][0]["formulation"] == "dcopf"
    assert asyncio.run(tellegen.contract())["contract"] == "tellegen.cli/1"
    assert [call["argv"] for call in fake_binary()] == [["capabilities"], ["contract"]]


def test_solve_hands_generation_two_ir_to_the_binary(fake_binary):
    result = asyncio.run(tellegen.solve(path=str(CASE9)))
    assert result["formulation"] == "dcopf"
    assert result["selection"] == {}
    assert result["value_type"] == "powerio.BalancedNetwork"
    assert result["diagnostics"] == [] and result["warnings"] == []
    # fidelity and the typed edit report belong to the powerio adapters.
    assert "fidelity" not in result and "lowering" not in result
    assert result["response"]["status"] == "optimal"
    assert len(result["response"]["lmp"]) == 9
    (call,) = fake_binary()
    assert json.loads(call["argv"][0]) == {"formulation": "dcopf"}
    module = json.loads(call["stdin"])
    assert module["schema"] == "pio-ir" and module["version"] == 2
    assert module["value"]["type"] == "powerio.BalancedNetwork"


def test_the_input_side_diagnostics_travel_with_every_response(fake_binary):
    """The module's own records reach the caller, not only the returned module's."""
    lowered = powerio.parse(DIST).to_balanced(1.0)
    ir = powerio.serialize(lowered).text
    codes = {record["code"] for record in tellegen._module_ir(ir, None, None, None, None)[1]["diagnostics"]}
    assert codes and all(code.startswith("TRANSFORM.MULTI_TO_BALANCED") for code in codes)

    solved = asyncio.run(tellegen.solve(powerio_ir=ir))
    assert {record["code"] for record in solved["diagnostics"]} == codes
    # A balanced transformation states remarks, and `warnings` carries error and
    # warning severities only, so the records are the ones that carry them.
    assert {record["severity"] for record in solved["diagnostics"]} == {"remark"}
    assert solved["warnings"] == []

    module = asyncio.run(tellegen.solve_module(powerio_ir=ir))
    # The stand-in echoes the module it was given, so its records repeat the
    # input side here; a real solution module carries none of its own.
    assert codes <= {record["code"] for record in module["diagnostics"]}
    assert module["diagnostics_counts"]["remark"] >= len(codes)
    assert set(module["warnings"]) == set(solved["warnings"])
    assert module["value_type"] == "powerio.BalancedNetwork"  # the stand-in echoes the input
    assert module["selection"] == {}

    planned = asyncio.run(tellegen.plan(json.dumps({"budget_mw": 1}), powerio_ir=ir))
    assert {record["code"] for record in planned["diagnostics"]} == codes
    assert planned["value_type"] == "powerio.BalancedNetwork"


def test_multiconductor_input_fails_before_the_native_process(fake_binary, tmp_path):
    """PowerMCP names the missing lowering instead of a subprocess diagnostic."""
    study = tmp_path / "study.json"
    for call in (
        lambda: tellegen.solve(path=str(DIST)),
        lambda: tellegen.solve_module(path=str(DIST)),
        lambda: tellegen.plan(json.dumps({"budget_mw": 1}), path=str(DIST)),
        lambda: tellegen.study_create(str(study), {"id": "s1", "request": "r"}, input_path=str(DIST)),
    ):
        with pytest.raises(ValueError, match="balanced network or a calculation instance"):
            asyncio.run(call())
    assert fake_binary() == []
    assert not study.exists()


def test_an_error_diagnostic_is_refused_before_the_native_process(fake_binary, tmp_path):
    """A module PowerIO marks with an error severity never reaches the binary."""
    study = tmp_path / "study.json"
    for call in (
        lambda: tellegen.solve(path=str(UNRESOLVED)),
        lambda: tellegen.solve_module(path=str(UNRESOLVED)),
        lambda: tellegen.plan(json.dumps({"budget_mw": 1}), path=str(UNRESOLVED)),
        lambda: tellegen.study_create(str(study), {"id": "s1", "request": "r"}, input_path=str(UNRESOLVED)),
    ):
        with pytest.raises(ValueError, match="fails validation"):
            asyncio.run(call())
    assert fake_binary() == []
    assert not study.exists()


def test_a_marked_balanced_module_is_refused_like_every_other_adapter(fake_binary, monkeypatch):
    """The severity gate is the one `resolve_solver_case` applies, on the same wording."""
    network = powerio.parse(CASE9).value

    class Diagnostic:
        code = "TEST.REFUSED"
        severity = "error"
        message = "the input states an unresolved identity"
        target = None

    class Marked:
        diagnostics = (Diagnostic(),)
        value = network

    monkeypatch.setattr(powerio, "parse", lambda *args, **kwargs: Marked())
    with pytest.raises(ValueError, match="fails validation: TEST.REFUSED"):
        asyncio.run(tellegen.solve(path=str(CASE9)))
    assert fake_binary() == []


def test_solve_passes_edits_sensitivities_and_bounds_arrays(fake_binary):
    ir = powerio.serialize(powerio.parse(CASE9)).text
    result = asyncio.run(tellegen.solve(
        powerio_ir=ir, formulation="dcpf",
        edits='{"deltas": {"5": 10.0}}', sensitivities='[{"kind": "lmp"}]', max_elements=2,
    ))
    (call,) = fake_binary()
    assert json.loads(call["argv"][0]) == {
        "formulation": "dcpf", "edits": {"deltas": {"5": 10.0}}, "sensitivities": [{"kind": "lmp"}],
    }
    assert result["response"]["lmp"] == {"truncated": True, "count": 9, "head": [{"id": 1, "value": 1.0}, {"id": 2, "value": 1.0}]}
    with pytest.raises(ValueError, match="formulation"):
        asyncio.run(tellegen.solve(powerio_ir=ir, formulation="acopf"))
    with pytest.raises(ValueError, match="exactly one"):
        asyncio.run(tellegen.solve())
    with pytest.raises(ValueError, match="edits must be JSON"):
        asyncio.run(tellegen.solve(powerio_ir=ir, edits="{not json"))


def test_solve_selects_a_collection_entry(fake_binary):
    network = powerio.parse(CASE9).value
    series = powerio.TimeSeries([network, network], time_points=[powerio.TimePoint("h0"), powerio.TimePoint("h1")])
    ir = powerio.serialize(powerio.PioModule.from_value(series)).text
    with pytest.raises(ValueError, match="time_index"):
        asyncio.run(tellegen.solve(powerio_ir=ir))
    result = asyncio.run(tellegen.solve(powerio_ir=ir, time_index=1))
    assert result["selection"] == {"time_index": 1}
    (call,) = fake_binary()
    assert json.loads(call["stdin"])["value"]["type"] == "powerio.BalancedNetwork"


def test_solve_module_writes_through_staging_and_refuses_overwrite(fake_binary, tmp_path):
    out = tmp_path / "solution.pio.json"
    result = asyncio.run(tellegen.solve_module(path=str(CASE9), out_path=str(out)))
    assert result["path"] == str(out)
    assert result["value_type"] == "powerio.BalancedNetwork"   # the stand-in echoes the network
    assert json.loads(out.read_text())["producer"]["name"] == "fake-tellegen"
    with pytest.raises(ValueError, match="overwrite"):
        asyncio.run(tellegen.solve_module(path=str(CASE9), out_path=str(out)))
    inline = asyncio.run(tellegen.solve_module(path=str(CASE9)))
    assert json.loads(inline["powerio_ir"])["producer"]["name"] == "fake-tellegen"
    assert [call["argv"] for call in fake_binary()] == [["solve-module"], ["solve-module"]]


def test_plan_sends_module_and_spec_and_returns_the_proposal(fake_binary, tmp_path):
    spec = {"objective": {"kind": "weighted_lmp"}, "budget_mw": 100}
    result = asyncio.run(tellegen.plan(json.dumps(spec), path=str(CASE9)))
    assert result["plan"]["spec"] == spec
    assert result["solution"]["value_type"] == "powerio.BalancedNetwork"
    assert json.loads(result["solution_powerio_ir"])["producer"]["name"] == "fake-tellegen"
    (call,) = fake_binary()
    request = json.loads(call["stdin"])
    assert request["module"]["schema"] == "pio-ir" and request["spec"] == spec
    with pytest.raises(ValueError, match="CapacityPlanSpec"):
        asyncio.run(tellegen.plan("", path=str(CASE9)))


def test_study_create_fills_the_input_from_a_grid_exchange_file(fake_binary, tmp_path):
    study = tmp_path / "study.json"
    result = asyncio.run(tellegen.study_create(
        str(study), {"id": "s1", "title": "t", "request": "lower prices", "formulation": "dcopf"},
        input_path=str(CASE9),
    ))
    assert result["revision"] == 1
    assert result["active_goal"] == {"id": "g", "request": "lower prices", "anchor_state": "base"}
    (call,) = fake_binary()
    request = json.loads(call["stdin"])
    assert json.loads(request["input"])["schema"] == "pio-ir"
    assert request["base_input"] == request["input"]
    assert json.loads(study.read_text())["input_has_ir"]


def test_apply_never_reaches_the_binary_and_progress_is_returned(fake_binary, tmp_path):
    study = tmp_path / "study.json"
    asyncio.run(tellegen.study_create(str(study), {"id": "s1", "input": "{}", "request": "r"}))
    with pytest.raises(ValueError, match="explicit native CLI"):
        asyncio.run(tellegen.study_run(str(study), 1, {"kind": "apply", "proposal": "p"}))
    assert not (tmp_path / "study.json.applied").exists()
    result = asyncio.run(tellegen.study_run(str(study), 1, {"kind": "inspect", "state": "base"}))
    assert result["revision"] == 2 and result["experiment"] == "e1"
    # The stand-in also logs a JSON trial line; only the event is progress.
    assert result["progress"] == [{"event": "study_checkpoint", "index": 1}]
    assert fake_binary()[-1]["argv"] == ["study", "run", str(study), "--progress"]


def test_binary_failure_surfaces_its_diagnostic(fake_binary):
    with pytest.raises(RuntimeError, match="tellegen: boom"):
        asyncio.run(tellegen._call(["boom"]))


def test_timeout_terminates_within_the_grace_window(fake_binary, monkeypatch):
    monkeypatch.setenv("FAKE_TELLEGEN_SLEEP", "30")
    monkeypatch.setenv("POWERMCP_TELLEGEN_TIMEOUT_SECONDS", "0.5")
    monkeypatch.setenv("POWERMCP_TELLEGEN_CANCEL_GRACE_SECONDS", "5")
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out"):
        asyncio.run(tellegen._call(["capabilities-slow"], raw_stdin=json.dumps({"schema": "pio-ir", "version": 2, "value": {"data": {}}})))
    assert time.monotonic() - started < 15


def test_paths_are_contained_for_every_filesystem_argument(fake_binary, tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    outside = tmp_path / "outside.pio.json"
    with pytest.raises(Exception, match="outside"):
        asyncio.run(tellegen.solve(path=str(CASE9)))
    inside = root / "case9.m"
    inside.write_text(CASE9.read_text())
    with pytest.raises(Exception, match="outside"):
        asyncio.run(tellegen.solve_module(path=str(inside), out_path=str(outside)))
    assert fake_binary() == []


REAL = os.environ.get("TELLEGEN_BIN")


@pytest.mark.skipif(not REAL, reason="set TELLEGEN_BIN to a compiled tellegen CLI")
def test_real_binary_solves_case9(monkeypatch):
    monkeypatch.setenv("POWERMCP_TELLEGEN_BINARY", REAL)
    caps = asyncio.run(tellegen.capabilities())
    assert any(entry["formulation"] == "dcopf" and entry["available"] for entry in caps["capabilities"])
    result = asyncio.run(tellegen.solve(path=str(CASE9)))
    assert result["response"]["status"] in {"optimal", "Optimal", "feasible", "Feasible"}
    assert "objective" in result["response"]
    assert result["value_type"] == "powerio.BalancedNetwork"
    assert result["selection"] == {} and result["diagnostics"] == []
    solution = asyncio.run(tellegen.solve_module(path=str(CASE9)))
    assert solution["value_type"] == "powerio.DcOpfSolution"
    assert solution["termination"] == "converged"
    assert solution["objective"] > 0
    with pytest.raises(ValueError, match="balanced network or a calculation instance"):
        asyncio.run(tellegen.solve(path=str(DIST)))
    contract = asyncio.run(tellegen.contract())
    assert contract["contract"] == "tellegen.cli/1"
