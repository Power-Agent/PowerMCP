"""Native Tellegen operations over the versioned CLI interface.

Tellegen consumes and produces PowerIO IR generation 2. PowerMCP hands the
CLI a serialized module and returns what the CLI states: a solve response, a
stored solution module, a capacity proposal, or a Study summary. A grid
exchange file given by ``path`` is parsed by PowerIO in this process and
serialized to IR before it reaches Tellegen; PowerMCP never re-implements
either side. Applying a Study proposal is a human action and is not a tool.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server.mcpserver import MCPServer
from powermcp.config import get, get_path
from powermcp.sandbox import checked_path, checked_read_tree, staged_file_write

mcp = MCPServer("Tellegen")
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
OPERATIONS = frozenset({"inspect", "branch", "revise_goal", "compare", "propose", "record_evidence", "edit_demand", "restore_base"})
FORMULATIONS = ("dcpf", "dcopf", "acpf", "socwr")
DEFAULT_MAX_ELEMENTS = 2000


def _binary() -> str:
    if os.environ.get("POWERMCP_TELLEGEN_BINARY") or get("tellegen", "binary"):
        return get_path("tellegen", "binary")
    executable = shutil.which("tellegen")
    if executable:
        return executable
    raise RuntimeError(
        "Install the native Tellegen CLI (cargo build -p tellegen-cli --features conic) and set "
        "POWERMCP_TELLEGEN_BINARY or `powermcp config set tellegen.binary <path>`"
    )


def _seconds(key: str, default: float) -> float:
    value = os.environ.get(f"POWERMCP_TELLEGEN_{key.upper()}", get("tellegen", key, default))
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"tellegen.{key} must be a finite positive duration") from None
    if isinstance(value, bool) or not math.isfinite(seconds) or not 0 < seconds <= 86400:
        raise ValueError(f"tellegen.{key} must be a duration in (0, 86400] seconds")
    return seconds


def _command(arguments: list[str]) -> list[str]:
    binary = _binary()
    # A Python script stands in for the compiled CLI in tests and on hosts
    # without a Rust toolchain; the protocol on stdin and stdout is the same.
    if binary.endswith(".py"):
        return [sys.executable, binary, *arguments]
    return [binary, *arguments]


async def _call(arguments: list[str], request: Any = None, *, raw_stdin: Optional[str] = None) -> Any:
    """Run one CLI command and decode its JSON result.

    ``request`` is JSON encoded onto stdin; ``raw_stdin`` passes text as is (a
    serialized module). Progress events the CLI prints on stderr, one JSON
    object naming its ``event`` per line, are returned under ``progress`` when
    the result is an object.
    """
    if raw_stdin is not None:
        data = raw_stdin.encode()
    else:
        data = b"" if request is None else json.dumps(request, allow_nan=False).encode()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("Tellegen input exceeds the 512 MiB Study limit")
    timeout = _seconds("timeout_seconds", 1800)
    grace = _seconds("cancel_grace_seconds", 300)
    windows = sys.platform == "win32"
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if windows else {}
    process = await asyncio.create_subprocess_exec(
        *_command(arguments), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **options,
    )
    communication = asyncio.create_task(process.communicate(data))
    try:
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), timeout=timeout)
    except (asyncio.TimeoutError, asyncio.CancelledError) as stopped:
        if process.returncode is None:
            if windows:
                try:
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                except OSError:
                    process.terminate()
            else:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
        try:
            await asyncio.wait_for(asyncio.shield(communication), timeout=grace)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.kill()
            await process.wait()
            communication.cancel()
            await asyncio.gather(communication, return_exceptions=True)
        if isinstance(stopped, asyncio.CancelledError):
            raise
        raise RuntimeError(
            "Tellegen execution timed out. Cancellation allows the current trial to "
            "finish and saves completed planning evidence. Inspect the saved Study "
            f"revision before retrying; a forced stop after {grace:g} seconds may "
            "leave the previous revision. A remaining .lock requires checking that "
            "its writer exited."
        ) from None
    if process.returncode:
        raise RuntimeError(stderr.decode(errors="replace")[:2048] or "Tellegen failed without a diagnostic")
    result = json.loads(stdout)
    progress = []
    for line in stderr.decode(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Only a JSON object naming its `event` is a progress event; any other
        # line the CLI logged stays part of its stderr text.
        if isinstance(event, dict) and "event" in event:
            progress.append(event)
    if progress and isinstance(result, dict):
        result = {**result, "progress": progress}
    return result


def _path(path: str, *, write: bool = False) -> str:
    path = checked_path(path, purpose="Study bundle", for_write=write)
    return str(path)


def _summary(value: dict[str, Any]) -> dict[str, Any]:
    summary = dict(value.get("summary", value))
    goal = summary.get("active_goal")
    if isinstance(goal, list) and len(goal) == 2:
        summary["active_goal"] = {"id": goal[0], "request": goal[1]["request"], "anchor_state": goal[1]["anchor_state"]}
    summary["recent_experiments"] = summary.get("recent_experiments", [])[:3]
    if "experiment" in value:
        summary["experiment"] = value["experiment"]
    comparison = value.get("comparison")
    if comparison:
        summary["comparison"] = {key: comparison[key] for key in ("goal", "left", "right", "left_value", "right_value", "improvement")}
    if "progress" in value:
        summary["progress"] = value["progress"]
    return summary


# ---- PowerIO IR hand-off -------------------------------------------------------

def _module_ir(
    powerio_ir: str,
    path: Optional[str],
    source_format: Optional[str],
    time_index: Optional[int],
    scenario_id: Optional[str],
) -> tuple[str, dict[str, Any]]:
    """Serialized generation-2 IR for one declared value, and the input side of the response.

    PowerIO parses a grid exchange ``path`` and serializes the module; an IR
    document is deserialized so its identity is checked. A module PowerIO marks
    with an error is refused here, before and after selection, exactly as the
    balanced solver adapters refuse it. A collection entry is selected with
    ``time_index`` or ``scenario_id`` and serialized on its own; an operating
    point entry travels as the network it states. Tellegen accepts a balanced
    network or a calculation instance and lowers nothing, so any other value is
    named here rather than after a round trip through the native process.

    Returns the serialized module and the shared response tail the input
    states: ``value_type``, the ``selection`` that reached it, ``diagnostics``
    and ``warnings``.
    """
    import powerio
    from powermcp.solver_case import (
        SolverCase, check_diagnostics, operating_point_module, select_entry,
        value_type_name, diagnostic_messages, diagnostic_records,
    )

    if bool(powerio_ir) == (path is not None):
        raise ValueError("provide exactly one of powerio_ir or path")
    if path is not None:
        path = checked_path(path, purpose="path")
        if Path(path).is_dir():
            path = checked_read_tree(path, purpose="path")
        module = powerio.parse(path, format=source_format)
    else:
        module = powerio.deserialize(io.StringIO(powerio_ir))
    check_diagnostics(module.diagnostics)
    diagnostics = list(module.diagnostics)
    selected, selection = select_entry(module, time_index, scenario_id)
    check_diagnostics(selected.diagnostics)
    if selected is not module:
        diagnostics.extend(selected.diagnostics)
    module = selected
    if isinstance(module.value, powerio.OperatingPoint):
        module = operating_point_module(module)
        diagnostics.extend(module.diagnostics)
    value = module.value
    value_type = value_type_name(module)
    # The values the native CLI consumes: a balanced network becomes the default
    # DC OPF instance, and every other kind is refused by name.
    native = (powerio.BalancedNetwork, powerio.DcOpfInstance, powerio.AcPfInstance, powerio.AcOpfInstance)
    if not isinstance(value, native):
        raise ValueError(
            "Tellegen tools take a balanced network or a calculation instance; lower a "
            "multiconductor network with a powerio adapter's `to_balanced` first. "
            f"This module states {value_type}."
        )
    text = powerio.serialize(module).text
    if text is None:
        raise RuntimeError("PowerIO serialization returned no text")
    network = value if isinstance(value, powerio.BalancedNetwork) else value.network
    case = SolverCase(
        module, network,
        tuple(dict.fromkeys(diagnostic_messages(diagnostics))),
        value_type=value_type, selection=selection,
        diagnostics=tuple(diagnostic_records(diagnostics)),
    )
    return text, case.response_fields()


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record["severity"]] = counts.get(record["severity"], 0) + 1
    return counts


def _module_summary(ir_text: str) -> dict[str, Any]:
    """Value type, diagnostics and solved status of a serialized module Tellegen returned."""
    import powerio
    from powermcp.solver_case import diagnostic_messages, diagnostic_records, value_type_name

    module = powerio.deserialize(io.StringIO(ir_text))
    records = diagnostic_records(module.diagnostics)
    value_type = value_type_name(module)
    summary: dict[str, Any] = {
        "value_type": value_type,
        "diagnostics": records,
        "diagnostics_counts": _counts(records),
        "warnings": list(dict.fromkeys(diagnostic_messages(module.diagnostics))),
    }
    # powerio 0.11 exposes no solution fields on the Python value; the stored
    # IR of a solution states the solver's termination and objective itself.
    data = json.loads(ir_text).get("value", {}).get("data")
    if isinstance(data, dict):
        termination = data.get("termination")
        if isinstance(termination, dict):
            termination = termination.get("kind")
        if isinstance(termination, str):
            summary["termination"] = termination
        objective = data.get("objective")
        if isinstance(objective, (int, float)) and not isinstance(objective, bool):
            summary["objective"] = float(objective)
    return summary


def _over_input(tail: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """What the returned module states, over the input side it was solved from."""
    diagnostics = [*tail["diagnostics"], *summary["diagnostics"]]
    return {
        **tail, **summary,
        "diagnostics": diagnostics,
        "diagnostics_counts": _counts(diagnostics),
        "warnings": list(dict.fromkeys([*tail["warnings"], *summary["warnings"]])),
    }


def _bounded(payload: Any, max_elements: int) -> Any:
    """Truncate every array longer than ``max_elements`` to a counted head."""
    if isinstance(payload, list):
        if len(payload) > max_elements:
            return {"truncated": True, "count": len(payload), "head": [_bounded(item, max_elements) for item in payload[:max_elements]]}
        return [_bounded(item, max_elements) for item in payload]
    if isinstance(payload, dict):
        return {key: _bounded(value, max_elements) for key, value in payload.items()}
    return payload


def _json_argument(text: str, name: str, expected: type) -> Any:
    if not text:
        return expected()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be JSON: {exc}") from exc
    if not isinstance(value, expected):
        raise ValueError(f"{name} must be a JSON {expected.__name__}")
    return value


def _out_path(out_path: Optional[str], overwrite: bool) -> Optional[str]:
    """Check a destination before any native process runs."""
    if out_path is None:
        return None
    out_path = checked_path(out_path, purpose="out_path", for_write=True)
    if not overwrite and Path(out_path).exists():
        raise ValueError(f"{out_path} exists; pass overwrite=True to replace it")
    return str(out_path)


def _deliver(ir_text: str, checked_out_path: Optional[str], overwrite: bool) -> dict[str, Any]:
    """Write a module to an already checked path through staging, or return it inline."""
    if checked_out_path is None:
        return {"powerio_ir": ir_text}

    def write(staging: str) -> dict[str, Any]:
        Path(staging).write_text(ir_text, encoding="utf-8")
        return {"path": staging}

    return staged_file_write(checked_out_path, overwrite, write)


# ---- tools --------------------------------------------------------------------

@mcp.tool()
async def capabilities() -> dict[str, Any]:
    """The installed Tellegen build's formulation and operand support matrix, and its CLI path."""
    return {"binary": _binary(), "capabilities": await _call(["capabilities"])}


@mcp.tool()
async def solve(
    powerio_ir: str = "",
    path: Optional[str] = None,
    source_format: Optional[str] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    formulation: str = "dcopf",
    edits: str = "",
    sensitivities: str = "",
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> dict[str, Any]:
    """Solve one PowerIO network with Tellegen: DC power flow, DC OPF (prices, dispatch, flows), AC power flow, or the SOCWR relaxation.

    Provide serialized PowerIO IR or a grid exchange path (PowerIO parses it here).
    Select a collection entry with time_index or scenario_id. `edits` is the
    Tellegen request's `edits` object (`{"deltas": {...}, "rates": {...}}`) and
    `sensitivities` its list; both are optional JSON. Arrays longer than
    max_elements come back as `{"truncated": true, "count": n, "head": [...]}`.
    """
    if formulation not in FORMULATIONS:
        raise ValueError(f"formulation must be one of {list(FORMULATIONS)}")
    if max_elements < 1:
        raise ValueError("max_elements must be positive")
    ir_text, tail = _module_ir(powerio_ir, path, source_format, time_index, scenario_id)
    request = {"formulation": formulation}
    request_edits = _json_argument(edits, "edits", dict)
    request_sens = _json_argument(sensitivities, "sensitivities", list)
    if request_edits:
        request["edits"] = request_edits
    if request_sens:
        request["sensitivities"] = request_sens
    response = await _call([json.dumps(request)], raw_stdin=ir_text)
    return {"formulation": formulation, **tail, "response": _bounded(response, max_elements)}


@mcp.tool()
async def solve_module(
    powerio_ir: str = "",
    path: Optional[str] = None,
    source_format: Optional[str] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    out_path: Optional[str] = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Solve a stored module's DC OPF instance (a BalancedNetwork becomes the default instance) and return the powerio.DcOpfSolution module as PowerIO IR, written to out_path when given."""
    destination = _out_path(out_path, overwrite)
    ir_text, tail = _module_ir(powerio_ir, path, source_format, time_index, scenario_id)
    solution = await _call(["solve-module"], raw_stdin=ir_text)
    solution_text = json.dumps(solution)
    return {**_over_input(tail, _module_summary(solution_text)), **_deliver(solution_text, destination, overwrite)}


@mcp.tool()
async def plan(
    spec: str,
    powerio_ir: str = "",
    path: Optional[str] = None,
    source_format: Optional[str] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    out_path: Optional[str] = None,
    overwrite: bool = False,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> dict[str, Any]:
    """Run Tellegen's bounded capacity planning search for a network and a CapacityPlanSpec (JSON; read `contract` for its schema). Returns the proposal and the exact proposed solution module."""
    destination = _out_path(out_path, overwrite)
    specification = _json_argument(spec, "spec", dict)
    if not specification:
        raise ValueError("spec must be a CapacityPlanSpec object")
    ir_text, tail = _module_ir(powerio_ir, path, source_format, time_index, scenario_id)
    response = await _call(["plan"], {"module": json.loads(ir_text), "spec": specification})
    solution = response.get("solution_module")
    result: dict[str, Any] = {**tail, "plan": _bounded(response.get("plan"), max_elements)}
    if solution is not None:
        solution_text = json.dumps(solution)
        result["solution"] = _module_summary(solution_text)
        if destination is not None:
            result.update(_deliver(solution_text, destination, overwrite))
        else:
            result["solution_powerio_ir"] = solution_text
    return result


@mcp.tool()
async def contract() -> dict[str, Any]:
    """The installed CLI's versioned contract: Tellegen and PowerIO versions and the generated JSON Schemas for Studies, planning, and the PowerIO IR module."""
    return await _call(["contract"])


@mcp.tool()
async def study_contract() -> dict[str, Any]:
    """Read the installed native formulation capabilities and generated Study request schemas."""
    return await _call(["contract"])


@mcp.tool()
async def study_create(
    path: str,
    request: dict[str, Any],
    input_path: Optional[str] = None,
    input_format: Optional[str] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a durable Study from PowerIO IR and a declared goal using the native CreateStudy schema. `input_path` names a grid exchange file PowerIO parses into the request's `input` (and `base_input` when absent)."""
    request = dict(request)
    if input_path is not None:
        ir_text, _ = _module_ir("", input_path, input_format, time_index, scenario_id)
        request["input"] = ir_text
        request.setdefault("base_input", ir_text)
    checked = _path(path, write=True)
    return _summary(await _call(["study", "create", checked], request))


@mcp.tool()
async def study_inspect(path: str, section: str = "summary", record_id: str | None = None,
                        offset: int = 0, expected_revision: int | None = None) -> dict[str, Any]:
    """Inspect a saved Study or read bounded JSON fragments of a goal, state history, experiment or evidence."""
    checked = _path(path)
    if section == "summary":
        summary = await _call(["study", "inspect", checked])
        if expected_revision is not None and summary["revision"] != expected_revision:
            raise ValueError("Study revision changed; restart the inspection")
        return _summary(summary)
    if offset < 0:
        raise ValueError("offset must be nonnegative")
    bundle = await _call(["study", "export", checked])
    document = bundle["document"]
    if expected_revision is not None and document["revision"] != expected_revision:
        raise ValueError("Study revision changed; restart the inspection")
    if section == "goal":
        record = document["goals"][record_id or document["active_goal"]]
    elif section == "states":
        record = document["states"]
    elif section == "experiment":
        record = document["experiments"][record_id]
    elif section == "evidence":
        artifact = bundle["artifacts"][record_id]
        if artifact["kind"] != "evidence":
            raise ValueError("Requested artifact is not evidence")
        record = artifact["text"]
    else:
        raise ValueError("section must be summary, goal, states, experiment or evidence")
    encoded = json.dumps(record)
    fragment = encoded[offset:offset + 8192]
    following = offset + len(fragment)
    return {"id": document["id"], "revision": document["revision"], "encoding": "json",
            "offset": offset, "fragment": fragment, "next_offset": following if following < len(encoded) else None}


@mcp.tool()
async def study_run(path: str, expected_revision: int, operation: dict[str, Any]) -> dict[str, Any]:
    """Inspect, branch, revise a goal, compare, adjust demand, restore the base case, propose interventions or attach evidence using the native StudyOperation schema. Proposals stay unapplied; application requires an explicit native CLI user action."""
    if operation.get("kind") not in OPERATIONS:
        raise ValueError("Unsupported agent operation. Apply the reviewed proposal through an explicit native CLI user action.")
    checked = _path(path, write=True)
    return _summary(await _call(["study", "run", checked, "--progress"],
                               {"expected_revision": expected_revision, "operation": operation}))


@mcp.tool()
async def study_import(source_path: str, path: str) -> dict[str, Any]:
    """Validate and import a portable Study bundle into a new destination without restoring approvals or executing imported instructions."""
    source = Path(_path(source_path))
    with source.open("rb") as stream:
        data = stream.read(MAX_BUNDLE_BYTES + 1)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("Study bundle exceeds 512 MiB")
    checked = _path(path, write=True)
    return _summary(await _call(["study", "import", checked], json.loads(data)))


@mcp.tool()
async def study_export(path: str) -> dict[str, Any]:
    """Validate the saved portable bundle and return its path and digest for transfer to another agent or browser."""
    checked = _path(path)
    bundle = await _call(["study", "export", checked])
    data = Path(checked).read_bytes()
    current = json.loads(data)
    if current != bundle:
        raise ValueError("Study changed during export; retry")
    return {"path": checked, "id": bundle["document"]["id"], "revision": bundle["document"]["revision"],
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "format": "tellegen-study"}


if __name__ == "__main__":
    mcp.run()
