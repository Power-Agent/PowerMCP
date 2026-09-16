"""Typed modules, explicit state selection and validation at the solver boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytest.importorskip("powerio", minversion="0.11.3")

import powerio  # noqa: E402

from powermcp.sandbox import PathNotAllowed  # noqa: E402
from powermcp.solver_case import resolve_solver_case, unique_diagnostics  # noqa: E402

CASE9 = Path(__file__).parent / "data" / "case9.m"


def ir(module):
    return powerio.serialize(module).text


def test_case_file_constructs_a_validated_instance():
    resolved = resolve_solver_case(file_path=str(CASE9))
    assert resolved.network.n_buses == 9
    assert isinstance(resolved.module, powerio.PioModule)
    assert resolved.package is None
    assert "mpc.bus" in resolved.emit("matpower").text


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_directory_case_refuses_a_symlinked_descendant_outside_roots(tmp_path, monkeypatch):
    root = tmp_path / "allowed"
    root.mkdir()
    dataset = root / "dataset"
    powerio.emit(powerio.parse(CASE9), "pypsa-csv", dataset)
    outside = tmp_path / "outside-buses.csv"
    (dataset / "buses.csv").replace(outside)
    (dataset / "buses.csv").symlink_to(outside)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(PathNotAllowed, match="outside its allowed MCP root"):
        resolve_solver_case(file_path=str(dataset), source_format="pypsa-csv")


def test_ir_preserves_auditable_context(tmp_path):
    source = tmp_path / "case.pio.json"
    source.write_text(ir(powerio.parse(CASE9)))
    resolved = resolve_solver_case(file_path=str(source))
    assert resolved.network.n_buses == 9
    assert resolved.package["schema"] == "pio-ir"
    assert resolved.package["generation"] == 2
    assert resolved.package["producer"]["name"] == "powerio"
    assert resolved.package["selection"] == {}


def test_invalid_identities_cannot_reuse_stale_diagnostics():
    document = json.loads(ir(powerio.parse(CASE9)))
    buses = document["value"]["data"]["buses"]
    buses[1]["id"] = buses[0]["id"]
    document["diagnostics"] = []
    with pytest.raises((ValueError, RuntimeError)):
        resolve_solver_case(network_json=json.dumps(document))


def test_nested_collections_require_explicit_selection():
    network = powerio.parse(CASE9).value
    series = powerio.TimeSeries([network, network], time_points=[powerio.TimePoint("h0"), powerio.TimePoint("h1")])
    scenarios = powerio.ScenarioSet({"base": series, "alternative": series})
    payload = ir(powerio.PioModule.from_value(scenarios))
    with pytest.raises(ValueError, match="scenario_id"):
        resolve_solver_case(network_json=payload)
    with pytest.raises(ValueError, match="time_index"):
        resolve_solver_case(network_json=payload, scenario_id="base")
    resolved = resolve_solver_case(network_json=payload, scenario_id="alternative", time_index=1)
    assert resolved.network.n_buses == 9
    assert resolved.package["selection"] == {"scenario_id":"alternative", "time_index":1}
    for index in (-1, True):
        with pytest.raises(ValueError, match="nonnegative integer"):
            resolve_solver_case(network_json=payload, scenario_id="base", time_index=index)
    with pytest.raises(ValueError, match="past the end of the TimeSeries; 2 entries"):
        resolve_solver_case(network_json=payload, scenario_id="base", time_index=2)
    with pytest.raises(ValueError) as absent:
        resolve_solver_case(network_json=payload, scenario_id="missing", time_index=0)
    assert "names no entry of the ScenarioSet" in str(absent.value)
    assert "alternative" in str(absent.value)


def test_each_collection_level_selects_on_its_own_module():
    """One selector resolves per level, so no level depends on another's order.

    PowerIO IR admits a TimeSeries inside a ScenarioSet, so the nested case
    here is a ScenarioSet of TimeSeries; the single level cases pin the same
    property for a collection of one kind.
    """
    network = powerio.parse(CASE9).value
    series = powerio.TimeSeries(
        [network, network], time_points=[powerio.TimePoint("h0"), powerio.TimePoint("h1")]
    )

    by_time = resolve_solver_case(network_json=ir(powerio.PioModule.from_value(series)), time_index=1)
    assert by_time.selection == {"time_index": 1}
    assert isinstance(by_time.module.value, powerio.BalancedNetwork)

    alone = powerio.ScenarioSet({"only": network})
    by_scenario = resolve_solver_case(
        network_json=ir(powerio.PioModule.from_value(alone)), scenario_id="only"
    )
    assert by_scenario.selection == {"scenario_id": "only"}
    assert isinstance(by_scenario.module.value, powerio.BalancedNetwork)

    scenarios = powerio.ScenarioSet({"base": series, "alternative": series})
    nested = resolve_solver_case(
        network_json=ir(powerio.PioModule.from_value(scenarios)),
        scenario_id="alternative",
        time_index=0,
    )
    assert nested.selection == {"scenario_id": "alternative", "time_index": 0}
    assert isinstance(nested.module.value, powerio.BalancedNetwork)
    assert "mpc.bus" in nested.emit("matpower").text


def test_calculation_instance_keeps_its_type():
    module = powerio.parse(CASE9).to_dc_opf_instance()
    resolved = resolve_solver_case(network_json=ir(module))
    assert isinstance(resolved.module.value, powerio.DcOpfInstance)
    assert resolved.network.n_buses == 9
    assert resolved.emit("matpower").text


def test_multiconductor_input_requires_explicit_lowering():
    payload = '{"meta":{"frequency":50},"bus":{"b":{"terminal_names":["a","b","c","n"]}}}'
    with pytest.raises(ValueError, match="explicitly call to_balanced"):
        resolve_solver_case(network_json=payload, source_format="bmopf-json")


def test_a_retired_package_document_is_not_powerio_ir():
    """A 0.9 Package carries no `pio-ir` schema, so no writer ever sees it.

    Named as PowerIO IR it is refused for what it is not; unnamed, powerio
    refuses it as an unknown JSON format. Either way the migration is the one
    the README states: re-parse the original case and pass its `powerio_ir`.
    """
    package = '{"model_kind":"balanced","model":{}}'
    with pytest.raises(ValueError, match="not PowerIO IR"):
        resolve_solver_case(network_json=package, source_format="pio-ir")
    with pytest.raises(ValueError, match="unknown or unsupported case format"):
        resolve_solver_case(network_json=package)


def test_study_commit_requires_a_tellegen_study():
    with pytest.raises(ValueError, match="Tellegen Study"):
        resolve_solver_case(file_path=str(CASE9), study_commit=0)


def test_exactly_one_input_and_matching_selectors_are_required():
    with pytest.raises(ValueError, match="exactly one"):
        resolve_solver_case()
    with pytest.raises(ValueError, match="exactly one"):
        resolve_solver_case(file_path="case.m", network_json="{}")
    with pytest.raises(ValueError, match="does not match"):
        resolve_solver_case(file_path=str(CASE9), time_index=0)


DIST = Path(__file__).parent / "data" / "opendss" / "fourwire_linecode.dss"


def test_powerio_ir_is_the_primary_argument_and_network_json_its_alias():
    payload = ir(powerio.parse(CASE9))
    primary = resolve_solver_case(powerio_ir=payload)
    alias = resolve_solver_case(network_json=payload)
    assert primary.network.n_buses == alias.network.n_buses == 9
    assert primary.value_type == "powerio.BalancedNetwork"
    assert primary.selection == {}
    assert isinstance(primary.diagnostics, tuple)
    with pytest.raises(ValueError, match="not both"):
        resolve_solver_case(powerio_ir=payload, network_json=payload)


def test_response_fields_carry_the_shared_tail():
    resolved = resolve_solver_case(file_path=str(CASE9))
    conversion = resolved.emit("matpower")
    fields = resolved.response_fields(conversion)
    assert fields["value_type"] == "powerio.BalancedNetwork"
    assert fields["selection"] == {}
    assert fields["fidelity"] in {"exact_same_format", "canonical"}
    assert isinstance(fields["diagnostics"], list) and isinstance(fields["warnings"], list)
    assert "edits" not in fields and "lowering" not in fields and "package" not in fields


def test_typed_edits_apply_before_the_solver_sees_the_network():
    base = powerio.parse(CASE9).value
    load = base.loads[0]
    load_id = load.get("uid") or "loads:0"
    branch_id = base.branches[0].get("uid") or "branches:0"
    edits = json.dumps([
        {"op": "set_load_active_power", "load": load_id, "mw": 91.5},
        {"op": "set_branch_thermal_rating", "branch": branch_id, "mva": 123.0},
        {"op": "set_bus_load_active_power", "bus": base.loads[1]["bus"], "mw": 77.0, "allocation": "equal"},
    ])
    resolved = resolve_solver_case(file_path=str(CASE9), edits=edits)
    network = resolved.network
    assert network.loads[0]["p"] == pytest.approx(91.5)
    assert network.branches[0]["rate_a"] == pytest.approx(123.0)
    assert network.loads[1]["p"] == pytest.approx(77.0)
    assert resolved.edits["connectivity_changed"] is False
    fields = {(change["component_type"], change["field"]) for change in resolved.edits["changes"]}
    assert ("load", "active_power") in fields or any(c["component_type"] == "load" for c in resolved.edits["changes"])
    assert any(change["component_type"] == "branch" for change in resolved.edits["changes"])
    # The emitted case carries the edit, so every solver adapter sees it.
    assert "91.5" in resolved.emit("matpower").text
    # The source module is untouched: a fresh resolution states the original demand.
    assert resolve_solver_case(file_path=str(CASE9)).network.loads[0]["p"] == pytest.approx(base.loads[0]["p"])


def two_loads_on_one_bus():
    """case9 with its first demand split into two 25 MW loads on the same bus."""
    document = json.loads(ir(powerio.parse(CASE9)))
    loads = document["value"]["data"]["loads"]
    shared = dict(loads[0])
    document["value"]["data"]["loads"] = [
        {**shared, "p": 25.0, "uid": "load-A"},
        {**shared, "p": 25.0, "uid": "load-B"},
        *loads[1:],
    ]
    document["value"]["data"]["generated_uids"] = []
    return json.dumps(document), shared["bus"]


def test_edits_apply_in_the_order_the_caller_listed_them():
    payload, bus = two_loads_on_one_bus()
    reallocate = {"op": "set_bus_load_active_power", "bus": bus, "mw": 50.0,
                  "allocation": "proportional_to_current_active_power"}
    set_load_a = {"op": "set_load_active_power", "load": "load-A", "mw": 10.0}

    # The reallocation runs first and the direct edit states the final value.
    resolved = resolve_solver_case(powerio_ir=payload, edits=json.dumps([reallocate, set_load_a]))
    assert resolved.network.loads[0]["p"] == pytest.approx(10.0)
    assert resolved.network.loads[1]["p"] == pytest.approx(25.0)
    assert [(change["local_id"], change["field"]) for change in resolved.edits["changes"]] == [
        ("load-A", "load_active_power"),
    ]

    # Reversed, the reallocation sees 10 and 25 MW and splits 50 MW over them.
    resolved = resolve_solver_case(powerio_ir=payload, edits=json.dumps([set_load_a, reallocate]))
    assert resolved.network.loads[0]["p"] == pytest.approx(50.0 * 10.0 / 35.0)
    assert resolved.network.loads[1]["p"] == pytest.approx(50.0 * 25.0 / 35.0)
    assert [change["local_id"] for change in resolved.edits["changes"]] == ["load-A", "load-A", "load-B"]


def test_consecutive_updates_of_one_class_are_one_batch_in_list_order():
    payload, _ = two_loads_on_one_bus()
    edits = json.dumps([
        {"op": "set_load_active_power", "load": "load-A", "mw": 10.0},
        {"op": "set_load_active_power", "load": "load-B", "mw": 40.0},
        {"op": "set_branch_thermal_rating", "branch": "1-4", "mva": 123.0},
        {"op": "set_load_active_power", "load": "load-A", "mw": 5.0},
    ])
    resolved = resolve_solver_case(powerio_ir=payload, edits=edits)
    assert resolved.network.loads[0]["p"] == pytest.approx(5.0)
    assert resolved.network.loads[1]["p"] == pytest.approx(40.0)
    assert resolved.network.branches[0]["rate_a"] == pytest.approx(123.0)
    assert [(change["component_type"], change["local_id"]) for change in resolved.edits["changes"]] == [
        ("load", "load-A"), ("load", "load-B"), ("branch", "1-4"), ("load", "load-A"),
    ]


def test_a_rejected_edit_states_its_diagnostic_code_once():
    with pytest.raises(ValueError) as rejected:
        resolve_solver_case(file_path=str(CASE9),
                            edits='[{"op": "set_load_active_power", "load": "loads:999", "mw": 1.0}]')
    message = str(rejected.value)
    assert message.startswith("edit rejected: ")
    codes = [word for word in message.split() if word.isupper() and "." in word]
    assert codes and message.count(codes[0]) == 1


def test_edits_are_validated_as_a_whole_before_anything_applies():
    base = powerio.parse(CASE9).value
    load_id = base.loads[0].get("uid") or "loads:0"
    for bad, message in (
        ('[{"op": "set_load_active_power", "load": "%s", "mw": 91.5}, {"op": "teleport"}]' % load_id, "unknown op"),
        ('[{"op": "set_load_active_power", "load": "%s", "mw": "big"}]' % load_id, "finite number"),
        ('[{"op": "set_branch_in_service", "branch": "branches:0", "in_service": "no"}]', "true or false"),
        ('[{"op": "set_bus_load_active_power", "bus": 5, "mw": 1.0, "allocation": "random"}]', "allocation"),
        ('{"op": "set_load_active_power"}', "JSON list"),
    ):
        with pytest.raises(ValueError, match=message):
            resolve_solver_case(file_path=str(CASE9), edits=bad)
    with pytest.raises(ValueError, match="edit rejected"):
        resolve_solver_case(file_path=str(CASE9), edits='[{"op": "set_load_active_power", "load": "loads:999", "mw": 1.0}]')


def test_unique_diagnostics_keeps_one_entry_per_report():
    """Equal reports collapse to the first; a distinct one keeps its place."""
    lowered = powerio.parse(DIST).to_balanced(1.0)
    first, second = list(lowered.diagnostics)[:2]
    assert (first.code, first.message) != (second.code, second.message)
    kept = unique_diagnostics([first, first, second])
    assert [(item.code, item.message) for item in kept] == [
        (first.code, first.message),
        (second.code, second.message),
    ]
    assert unique_diagnostics([]) == []


def test_multiconductor_lowering_is_an_explicit_choice_with_a_report():
    with pytest.raises(ValueError, match="to_balanced"):
        resolve_solver_case(file_path=str(DIST))
    resolved = resolve_solver_case(file_path=str(DIST), to_balanced=True, base_mva=1.0)
    assert isinstance(resolved.network, powerio.BalancedNetwork)
    assert resolved.network.n_buses >= 2
    assert resolved.lowering is not None
    assert "ready" in resolved.lowering
    fields = resolved.response_fields()
    assert fields["lowering"] == resolved.lowering
    assert fields["value_type"] == "powerio.MulticonductorNetwork"
    reported = [(record["code"], record["message"]) for record in fields["diagnostics"]]
    assert any(code.startswith("TRANSFORM.MULTI_TO_BALANCED.") for code, _ in reported)
    assert len(reported) == len(set(reported))


def test_operating_point_entries_reach_the_solver_as_their_network():
    network = powerio.parse(CASE9).value
    document = json.loads(ir(powerio.PioModule.from_value(network)))
    series = {
        "schema": document["schema"], "version": document["version"], "producer": document["producer"],
        "value": {
            "type": "powerio.TimeSeries<powerio.OperatingPoint<powerio.BalancedNetwork>>",
            "data": {
                "network": document["value"]["data"],
                "time_points": [{"label": "h0"}, {"label": "h1"}],
                "values": [{"quantities": {}}, {"quantities": {}}],
            },
        },
    }
    resolved = resolve_solver_case(powerio_ir=json.dumps(series), time_index=1)
    assert resolved.network.n_buses == 9
    assert resolved.selection == {"time_index": 1}
    assert "mpc.bus" in resolved.emit("matpower").text


def test_temporary_integration_module_names_are_absent():
    package_dir = Path(__file__).parents[1] / "powermcp"
    assert not (package_dir / "powerio_bridge.py").exists()
    assert not (package_dir / "powerio_server.py").exists()
    assert not (package_dir / "powerio_handoff.py").exists()
