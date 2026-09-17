"""Select one typed PowerIO state for a balanced solver.

PowerIO owns parsing, IR validation, transformations, typed updates and format
emission. PowerMCP routes a declared PowerIO value to the solver that accepts
it: the caller names the collection entry, asks for the multiconductor to
balanced transformation explicitly, and states any what-if edit as a typed
update PowerIO validates and applies, in the caller's order, before the solver
sees the network. Nothing here re-parses, re-validates, or recomputes what
PowerIO already states.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import powerio
from powermcp.sandbox import checked_path, checked_read_tree

_IR_FORMATS = frozenset({"pio-ir", "pio"})
IR_SCHEMA = "pio-ir"
IR_VERSION = 2


_QUIET_SEVERITIES = frozenset({"remark", "note"})


def diagnostic_messages(items: Any) -> tuple[str, ...]:
    """Keep stable diagnostic codes beside their user-facing descriptions."""
    return tuple(
        f"{item.code}: {item.message}"
        for item in items
        if item.severity not in _QUIET_SEVERITIES
    )


def unique_diagnostics(items: Any) -> list[Any]:
    """The diagnostics in first-seen order, one entry per distinct report.

    A module states the records of every stage that produced it, so a stage
    whose diagnostics were collected when it ran states them again through the
    module it handed on. Identity is the stable code, its severity, the
    description, the target and the component id.
    """
    seen: set[tuple[Any, ...]] = set()
    unique: list[Any] = []
    for item in items:
        key = (item.code, item.severity, item.message, item.target, item.id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def check_diagnostics(items: Any) -> None:
    failures = [item for item in items if item.severity == "error"]
    if failures:
        raise ValueError(
            "PowerIO input fails validation: " + "; ".join(diagnostic_messages(failures))
        )


@dataclass(frozen=True)
class SolverCase:
    """One selected state, its typed network and its source context.

    ``module`` is the single-entry module a writer receives; ``network`` its
    balanced network. ``package`` keeps the IR context adapters already return
    (schema, generation, producer, value type, selection). ``value_type`` is the
    PowerIO structural type of the selected value, ``selection`` the collection
    selectors that reached it, ``diagnostics`` the module's records, ``edits``
    the report of the typed updates applied, and ``lowering`` the multiconductor
    readiness report when the caller asked for the balanced transformation.
    """
    module: powerio.PioModule
    network: powerio.BalancedNetwork
    warnings: tuple[str, ...] = ()
    package: dict[str, Any] | None = None
    value_type: str = "powerio.BalancedNetwork"
    selection: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()
    edits: dict[str, Any] | None = None
    lowering: dict[str, Any] | None = None

    def emit(self, format: str, destination: Any = None):
        result = powerio.emit(self.module, format, destination)
        check_diagnostics(result.diagnostics)
        return result

    def response_fields(self, conversion: Any = None) -> dict[str, Any]:
        """The shared tail every solver adapter splices into its response.

        ``conversion`` is the ``EmitResult`` of the adapter's own emission, so
        its fidelity and diagnostics travel with the module's.
        """
        diagnostics = list(self.diagnostics)
        warnings = list(self.warnings)
        fields: dict[str, Any] = {
            "value_type": self.value_type,
            "selection": dict(self.selection),
        }
        if conversion is not None:
            diagnostics.extend(powerio.diagnostic_records(conversion.diagnostics))
            warnings.extend(diagnostic_messages(conversion.diagnostics))
            fields["fidelity"] = conversion.fidelity
        fields["diagnostics"] = diagnostics
        fields["warnings"] = list(dict.fromkeys(warnings))
        if self.edits is not None:
            fields["edits"] = self.edits
        if self.lowering is not None:
            fields["lowering"] = self.lowering
        if self.package is not None:
            fields["package"] = self.package
        return fields


def _document(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    if value.get("schema") == IR_SCHEMA:
        return value
    return None


def select_entry(module, time_index, scenario_id):
    """Resolve the collection selectors to one entry and the module holding it.

    Each level rebuilds the module around the entry it selected, so an entry
    carries exactly one selector and the levels of a nested collection resolve
    outermost first. A selector naming an absent scenario or an index past the
    end raises :class:`ValueError` stating what the collection offers.
    """
    selection = {}
    value = module.value
    while isinstance(value, (powerio.TimeSeries, powerio.ScenarioSet)):
        if isinstance(value, powerio.ScenarioSet):
            available = list(value.keys())[:20]
            if scenario_id is None:
                raise ValueError(
                    f"select scenario_id from the ScenarioSet before solving; scenarios: {available}"
                )
            if scenario_id not in value:
                raise ValueError(
                    f"scenario_id {scenario_id!r} names no entry of the ScenarioSet; "
                    f"scenarios: {available}"
                )
            value = value[scenario_id]
            selection["scenario_id"] = scenario_id
            scenario_id = None
        else:
            if time_index is None:
                raise ValueError(
                    f"select time_index from the TimeSeries before solving; {len(value)} entries"
                )
            if isinstance(time_index, bool) or not isinstance(time_index, int) or time_index < 0:
                raise ValueError("time_index must be a nonnegative integer")
            if time_index >= len(value):
                raise ValueError(
                    f"time_index {time_index} is past the end of the TimeSeries; "
                    f"{len(value)} entries"
                )
            value = value[time_index]
            selection["time_index"] = time_index
            time_index = None
        module = powerio.PioModule.from_value(value)
        value = module.value
    if time_index is not None or scenario_id is not None:
        raise ValueError("state selector does not match the input collection")
    return module, selection


# ---- typed edits -------------------------------------------------------------

# Each op names the PowerIO constructor, the component type the id refers to,
# and the value keys with the unit constructor that types them.
_OPERATING_POINT_OPS: dict[str, tuple[str, str, tuple[tuple[str, str], ...], bool]] = {
    # op: (constructor, component_type, ((key, unit), ...), takes_terminal)
    "set_load_active_power": ("set_load_active_power", "load", (("mw", "active_power"),), True),
    "set_load_reactive_power": ("set_load_reactive_power", "load", (("mvar", "reactive_power"),), True),
    "set_generator_active_power": ("set_generator_active_power", "generator", (("mw", "active_power"),), True),
    "set_generator_reactive_power": ("set_generator_reactive_power", "generator", (("mvar", "reactive_power"),), True),
    "set_generator_voltage_magnitude": ("set_generator_voltage_magnitude", "generator", (("vm_pu", "float"),), False),
    "set_generator_in_service": ("set_generator_in_service", "generator", (("in_service", "bool"),), False),
    "set_branch_in_service": ("set_branch_in_service", "branch", (("in_service", "bool"),), False),
    "set_transformer_tap_ratio": ("set_transformer_tap_ratio", "transformer", (("tap_ratio", "float"),), False),
    "set_transformer_phase_shift": ("set_transformer_phase_shift", "transformer", (("shift_degrees", "float"),), False),
    "set_switch_closed": ("set_switch_closed", "switch", (("closed", "bool"),), False),
}
_NETWORK_OPS = {
    "set_branch_thermal_rating": ("set_branch_thermal_rating", "branch", (("mva", "apparent_power"),), True),
}
_BUS_LOAD_OP = "set_bus_load_active_power"
_ALLOCATIONS = ("proportional_to_current_active_power", "equal")
EDIT_OPS: tuple[str, ...] = (*_OPERATING_POINT_OPS, *_NETWORK_OPS, _BUS_LOAD_OP)


def parse_edits(text: str | None) -> list[dict[str, Any]]:
    """Decode the ``edits`` JSON argument: a list of ``{"op": ..., ...}`` objects."""
    if not text:
        return []
    try:
        edits = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"edits must be a JSON list of objects: {exc}") from exc
    if not isinstance(edits, list) or not all(isinstance(edit, dict) for edit in edits):
        raise ValueError("edits must be a JSON list of objects")
    return edits


def _number(edit: dict[str, Any], key: str, position: int) -> float:
    value = edit.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"edit #{position}: {key!r} must be a finite number")
    return float(value)


def _flag(edit: dict[str, Any], key: str, position: int) -> bool:
    value = edit.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"edit #{position}: {key!r} must be true or false")
    return value


def _identity(edit: dict[str, Any], component_type: str, position: int) -> powerio.ComponentId:
    local_id = edit.get(component_type)
    if local_id is None or isinstance(local_id, bool):
        raise ValueError(f"edit #{position}: {component_type!r} names the component's stable id")
    return powerio.ComponentId(component_type, str(local_id))


def _typed_value(kind: str, edit: dict[str, Any], key: str, position: int) -> Any:
    if kind == "active_power":
        return powerio.ActivePower.megawatts(_number(edit, key, position))
    if kind == "reactive_power":
        return powerio.ReactivePower.megavars(_number(edit, key, position))
    if kind == "apparent_power":
        return powerio.ApparentPower.megavolt_amperes(_number(edit, key, position))
    if kind == "bool":
        return _flag(edit, key, position)
    return _number(edit, key, position)


def _build_updates(edits: list[dict[str, Any]]) -> list[tuple[str, Any]]:
    """Validate every edit first, then build the typed updates as ordered steps.

    A step is one run of consecutive edits of a single update class, or one bus
    demand reallocation, which PowerIO applies on its own at the calculation
    level. The steps keep the caller's list order, so a later edit states the
    value that stands after the edits before it.
    """
    steps: list[tuple[str, Any]] = []
    for position, edit in enumerate(edits):
        op = edit.get("op")
        if op in _OPERATING_POINT_OPS or op in _NETWORK_OPS:
            operating = op in _OPERATING_POINT_OPS
            table = _OPERATING_POINT_OPS if operating else _NETWORK_OPS
            constructor, component_type, values, takes_terminal = table[op]
            identity = _identity(edit, component_type, position)
            args = [_typed_value(kind, edit, key, position) for key, kind in values]
            kwargs = {}
            if takes_terminal and edit.get("terminal") is not None:
                kwargs["terminal"] = str(edit["terminal"])
            klass = powerio.OperatingPointUpdate if operating else powerio.NetworkUpdate
            update = getattr(klass, constructor)(identity, *args, **kwargs)
            step = "operating" if operating else "network"
            if steps and steps[-1][0] == step:
                steps[-1][1].append(update)
            else:
                steps.append((step, [update]))
        elif op == _BUS_LOAD_OP:
            bus = edit.get("bus")
            if isinstance(bus, bool) or not isinstance(bus, int):
                raise ValueError(f"edit #{position}: 'bus' must be an integer bus id")
            allocation = edit.get("allocation", _ALLOCATIONS[0])
            if allocation not in _ALLOCATIONS:
                raise ValueError(f"edit #{position}: 'allocation' must be one of {list(_ALLOCATIONS)}")
            total = powerio.ActivePower.megawatts(_number(edit, "mw", position))
            steps.append(("bus_load", (bus, total, allocation)))
        else:
            raise ValueError(f"edit #{position}: unknown op {op!r}; expected one of {list(EDIT_OPS)}")
    return steps


def _report_payload(reports: list[Any]) -> dict[str, Any]:
    changes = []
    connectivity = False
    for report in reports:
        connectivity = connectivity or bool(report.connectivity_changed)
        for change in report.changes:
            changes.append(
                {
                    "component_type": change.component_id.component_type,
                    "local_id": change.component_id.local_id,
                    "field": change.field,
                    "terminal": change.terminal,
                }
            )
    return {"changes": changes, "connectivity_changed": connectivity}


def apply_edits(
    module: powerio.PioModule, edits: list[dict[str, Any]]
) -> tuple[powerio.PioModule, dict[str, Any] | None]:
    """Apply the edit vocabulary to a module with PowerIO's typed updates.

    The whole list is validated before anything is applied, and the edits then
    apply in the caller's list order. Consecutive updates of one class go
    through one atomic ``apply_updates`` batch on the module; each bus demand
    reallocation is its own step and therefore sees the values the edits before
    it produced. A bus demand allocation is a calculation level operation in
    PowerIO, so it runs on a DC power flow instance built from the network at
    that point and the edited network comes back as a fresh module. Returns the
    module to continue with and the merged report, whose changes follow
    application order, or ``None`` for an empty list.
    """
    if not edits:
        return module, None
    steps = _build_updates(edits)
    value = module.value
    wrap = None
    if isinstance(value, powerio.BalancedNetwork):
        pass
    elif isinstance(value, (
        powerio.DcPfInstance, powerio.AcPfInstance, powerio.DcOpfInstance, powerio.AcOpfInstance,
    )):
        wrap = powerio.CalculationUpdate
    else:
        raise ValueError(
            f"edits apply to a BalancedNetwork or a calculation instance, not {type(value).__name__}"
        )
    reports = []
    try:
        for step, payload in steps:
            if step == "bus_load":
                bus, total, allocation = payload
                target = module if wrap else module.to_dc_pf_instance()
                reports.append(powerio.apply_bus_load_active_power(target, bus, total, allocation=allocation))
                if not wrap:
                    module = powerio.PioModule.from_value(target.value.network)
            else:
                updates = [wrap(update) for update in payload] if wrap else payload
                reports.append(powerio.apply_updates(module, updates))
    except (powerio.PowerIOError, TypeError) as exc:
        # PowerIOError.__str__ already states the stable diagnostic code.
        raise ValueError(f"edit rejected: {exc}") from exc
    return module, _report_payload(reports)


# ---- resolution ---------------------------------------------------------------

_MULTICONDUCTOR = (
    powerio.MulticonductorNetwork,
    powerio.McAcPfInstance,
    powerio.McAcOpfInstance,
    powerio.McAcPfSolution,
    powerio.McAcOpfSolution,
)


def operating_point_module(module: powerio.PioModule) -> powerio.PioModule:
    """The balanced network an operating point entry states."""
    return powerio.PioModule.from_value(module.value.network)


def resolve_solver_case(
    *,
    file_path: str | None = None,
    network_json: str | None = None,
    powerio_ir: str | None = None,
    source_format: str | None = None,
    time_index: int | None = None,
    scenario_id: str | None = None,
    operating_point: int | None = None,
    study_commit: int | None = None,
    edits: str | list[dict[str, Any]] | None = None,
    to_balanced: bool = False,
    base_mva: float = 100.0,
) -> SolverCase:
    """Resolve one file or IR input without selecting or lowering implicitly.

    ``powerio_ir`` is the serialized module the powerio server's ``parse``,
    ``to_normalized`` or ``to_balanced`` tools return; ``network_json`` is its
    compatibility alias and must carry the same generation-2 document.
    ``operating_point`` is a compatibility spelling for ``time_index``. Study
    history belongs to Tellegen; legacy package commits require migration.
    ``edits`` are typed updates applied before validation; ``to_balanced``
    authorizes the multiconductor to balanced transformation, whose readiness
    report is returned as ``lowering``.
    """
    if network_json and powerio_ir:
        raise ValueError("pass powerio_ir or its alias network_json, not both")
    network_json = powerio_ir or network_json or None
    if (file_path is None) == (network_json is None):
        raise ValueError("provide exactly one of file_path or powerio_ir")
    if study_commit is not None:
        raise ValueError("study_commit requires a Tellegen Study state; export its PowerIO IR before using this solver")
    if operating_point is not None:
        if time_index is not None:
            raise ValueError("choose time_index or operating_point, not both")
        time_index = operating_point
    edit_list = parse_edits(edits) if isinstance(edits, str) or edits is None else list(edits)
    token = source_format.strip().lower().replace("_", "-") if source_format else None
    explicit_ir = token in _IR_FORMATS
    document = None
    if file_path is not None:
        path = Path(checked_path(file_path, purpose="file_path"))
        if path.is_dir():
            path = Path(checked_read_tree(str(path), purpose="file_path"))
        elif explicit_ir or path.suffix.lower() == ".json":
            document = _document(path.read_text(encoding="utf-8"))
        if explicit_ir and document is None:
            raise ValueError("input is not PowerIO IR")
        module = powerio.deserialize(path) if document is not None else powerio.parse(path, format=token)
    else:
        document = _document(network_json)
        if explicit_ir and document is None:
            raise ValueError("input is not PowerIO IR")
        payload = network_json.encode("utf-8")
        module = powerio.deserialize(payload) if document is not None else powerio.parse(payload, format=token, name="input.json")
    check_diagnostics(module.diagnostics)
    diagnostics = list(module.diagnostics)
    module, selection = select_entry(module, time_index, scenario_id)
    check_diagnostics(module.diagnostics)
    value = module.value
    if isinstance(value, powerio.OperatingPoint):
        module = operating_point_module(module)
        value = module.value
    selected_type = module.type_name
    lowering = None
    if isinstance(value, _MULTICONDUCTOR):
        if not to_balanced or not isinstance(value, powerio.MulticonductorNetwork):
            raise ValueError(
                "this solver requires a balanced network; inspect PioModule.to_balanced_report() "
                "and explicitly call to_balanced() first, or pass to_balanced=True"
            )
        lowering = module.to_balanced_report(base_mva)
        module = module.to_balanced(base_mva)
        check_diagnostics(module.diagnostics)
        diagnostics.extend(module.diagnostics)
        value = module.value
    module, edit_report = apply_edits(module, edit_list)
    value = module.value
    if isinstance(value, powerio.BalancedNetwork):
        # Constructing an instance checks electrical identities and reference coverage.
        checked = module.to_ac_pf_instance()
        check_diagnostics(checked.diagnostics)
        network = module.value
    elif isinstance(value, (
        powerio.DcPfInstance, powerio.AcPfInstance, powerio.DcOpfInstance, powerio.AcOpfInstance,
        powerio.DcPfSolution, powerio.AcPfSolution, powerio.DcOpfSolution, powerio.AcOpfSolution,
        powerio.SocwrOpfSolution,
    )):
        network = module.value.network
    else:
        raise ValueError(f"unsupported solver input type: {type(value).__name__}")
    context = None
    if document is not None:
        context = {"schema": IR_SCHEMA, "generation": document["version"],
                   "producer": document.get("producer"), "source_type": document["value"]["type"],
                   "selection": selection}
    # A stage that handed its module on keeps its records here, and a stage
    # whose module reached the end states them again; report each one once.
    all_diagnostics = unique_diagnostics([*diagnostics, *module.diagnostics])
    warnings = tuple(dict.fromkeys(diagnostic_messages(all_diagnostics)))
    return SolverCase(
        module,
        network,
        warnings,
        context,
        value_type=selected_type,
        selection=selection,
        diagnostics=tuple(powerio.diagnostic_records(all_diagnostics)),
        edits=edit_report,
        lowering=lowering,
    )
