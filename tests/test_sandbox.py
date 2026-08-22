"""Containment for model supplied paths.

A tool argument is whatever the model was persuaded to ask for, so a tool that
takes a path and opens it reads or writes wherever the model points. The policy
is powerio's; these tests are the consumer suite over it, and they hold every
bridge server to actually using it.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import re

import pytest

import powerio.mcp.sandbox
import powermcp.sandbox
from PSLF import pslf_mcp
from PSSE import psse_mcp
from powermcp.sandbox import (
    PathNotAllowed,
    allowed_roots,
    checked_path,
    checked_read_tree,
    ensure_checked_directory,
    staged_directory_write,
)

REPO = pathlib.Path(__file__).resolve().parent.parent

# Every spelling powerio reads, so a test can clear them all before asserting
# that an unconfigured installation constrains nothing.
ROOT_ENVS = (powermcp.sandbox.ALLOWED_ROOTS_ENV,) + powermcp.sandbox.LEGACY_ROOT_ENVS

# Every server tool that takes a path from the model, and the argument it takes.
GUARDED = {
    "pandapower/panda_mcp.py": {
        "load_network": ["file_path"],
        "load_network_from_any": ["file_path"],
    },
    "PyPSA/pypsa_mcp.py": {
        "get_network_info": ["network_name"],
        "load_network": ["file_path"],
        "run_power_flow": ["network_name"],
        "run_contingency_analysis": ["network_name"],
        "get_component_details": ["network_name"],
        "add_bus": ["network_name"],
        "add_generator": ["network_name"],
        "add_load": ["network_name"],
        "add_line": ["network_name"],
        "add_storage_unit": ["network_name"],
        "optimize_network": ["network_name"],
        "optimize_investment": ["network_name"],
        "import_from_csv_folder": ["folder_path", "output_path"],
        "export_to_csv_folder": ["network_name", "folder_path"],
        "import_case_from_any": ["file_path", "output_path"],
        "import_case_from_json": ["output_path"],
    },
    "Egret/egret_mcp.py": {
        "solve_unit_commitment_problem": ["case_file"],
        "solve_ac_opf": ["case_file"],
        "solve_dc_opf": ["case_file"],
        "load_model_from_any": ["file_path"],
    },
    "ANDES/andes_mcp.py": {
        "run_power_flow": ["file_path"],
        "run_eigenvalue_analysis": ["file_path"],
        "load_network_from_json": ["out_path"],
        "load_network_from_any": ["file_path", "out_path"],
    },
    "surge/surge_mcp.py": {
        "load_network": ["file_path"],
        "save_network": ["file_path"],
        "export_tables": ["output_dir"],
    },
    "PowerWorld/powerworld_mcp.py": {
        "open_case": ["case_path"],
    },
    "LTSpice/ltspice_mcp.py": {
        "read_simulation_log": ["log_file_path"],
        "list_available_traces": ["raw_file_path"],
        "plot_specific_traces": ["raw_file_path", "session_dir"],
        "run_simulation": ["netlist_path", "session_dir"],
        "view_netlist_in_ltspice": ["netlist_path"],
    },
    "OpenDSS/opendss_tools/configuration.py": {
        "compile_opendss_file": ["dss_file"],
    },
    "PSSE/psse_mcp.py": {
        "open_case": ["case"],
    },
    "PSLF/pslf_mcp.py": {
        "open_case": ["case"],
    },
    "PLEXOSDB/plexosdb_mcp/main.py": {
        "translate_to_sienna": ["xml_path", "output_path"],
        "compare_solutions": ["xml_path_a", "xml_path_b"],
    },
}


def test_the_policy_is_powerios(monkeypatch):
    """The policy has one implementation, which both sides reach by identity.

    The drift this guards against already happened once: two copies read
    different environment variables, so an operator could configure containment
    and get it on one server and not another.
    """
    assert powermcp.sandbox.checked_path is powerio.mcp.sandbox.checked_path
    assert powermcp.sandbox.allowed_roots is powerio.mcp.sandbox.allowed_roots
    assert (
        powermcp.sandbox.check_allowed_read_tree
        is powerio.mcp.sandbox.check_allowed_read_tree
    )
    assert (
        powermcp.sandbox.checked_read_tree
        is powerio.mcp.sandbox.checked_read_tree
    )
    assert (
        powermcp.sandbox.staged_directory_write
        is powerio.mcp.sandbox.staged_directory_write
    )


@pytest.mark.parametrize("env", ROOT_ENVS)
def test_every_root_spelling_configures_containment(tmp_path, monkeypatch, env):
    root = tmp_path / "cases"
    root.mkdir()
    (tmp_path / "secret.m").write_text("")
    for name in ROOT_ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(env, str(root))
    assert allowed_roots() == (root.resolve(),)
    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        checked_path(str(tmp_path / "secret.m"), purpose="file_path")


def test_unset_roots_constrain_nothing(tmp_path, monkeypatch):
    for name in ROOT_ENVS:
        monkeypatch.delenv(name, raising=False)
    assert allowed_roots() == ()
    assert checked_path(str(tmp_path / "anywhere.m"), purpose="p")


def test_a_path_inside_a_root_is_admitted(tmp_path, monkeypatch):
    root = tmp_path / "cases"
    root.mkdir()
    case = root / "c.m"
    case.write_text("")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    assert checked_path(str(case), purpose="file_path") == str(case)


def test_a_path_outside_every_root_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "cases"
    root.mkdir()
    outside = tmp_path / "secret.m"
    outside.write_text("")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        checked_path(str(outside), purpose="file_path")


def test_dot_dot_does_not_climb_out(tmp_path, monkeypatch):
    root = tmp_path / "cases"
    root.mkdir()
    (tmp_path / "secret.m").write_text("")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        checked_path(str(root / ".." / "secret.m"), purpose="file_path")


@pytest.mark.skipif(os.name == "nt", reason="posix symlink semantics")
def test_a_symlink_is_judged_by_its_target(tmp_path, monkeypatch):
    root = tmp_path / "cases"
    root.mkdir()
    secret = tmp_path / "secret.m"
    secret.write_text("")
    (root / "innocent.m").symlink_to(secret)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        checked_path(str(root / "innocent.m"), purpose="file_path")


@pytest.mark.skipif(os.name == "nt", reason="posix symlink semantics")
def test_a_write_through_a_dangling_symlink_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "out"
    root.mkdir()
    (root / "new.m").symlink_to(tmp_path / "elsewhere.m")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))
    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        checked_path(str(root / "new.m"), purpose="output_path", for_write=True)


def test_a_remote_uri_is_not_a_local_path(monkeypatch):
    for name in ROOT_ENVS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(PathNotAllowed, match="must be a local path"):
        checked_path("https://example.invalid/case.m", purpose="file_path")


def test_a_file_uri_decodes(tmp_path, monkeypatch):
    case = tmp_path / "a b.m"
    case.write_text("")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    assert checked_path(case.as_uri(), purpose="file_path") == str(case)


def test_generated_directory_checks_and_creates_each_component(tmp_path, monkeypatch):
    root = tmp_path / "allowed"
    root.mkdir()
    target = root / "nested" / "results"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))

    assert ensure_checked_directory(str(target), purpose="output") == str(target)
    assert target.is_dir()


def test_generated_directory_stops_at_an_unavailable_anchor(monkeypatch):
    class UnavailableAnchor:
        parent = None

        def __init__(self):
            self.parent = self

        def exists(self):
            return False

        def __str__(self):
            return "Z:\\"

    anchor = UnavailableAnchor()
    monkeypatch.setattr(powermcp.sandbox, "decode_local_path", lambda *_a, **_k: anchor)

    with pytest.raises(PathNotAllowed, match="filesystem anchor does not exist"):
        ensure_checked_directory("Z:\\missing", purpose="output")


def _checked_arguments(server: str) -> dict[str, set[str]]:
    """Per tool, the arguments assigned from a ``checked_path`` call.

    Reads the server source rather than importing it: a bridge server pulls in
    the simulator it wraps, which is not installed in every environment, so
    importing to introspect would skip the check exactly where it matters. The
    guard is a syntactic property and the AST shows it.
    """
    tree = ast.parse((REPO / server).read_text(encoding="utf-8"))
    return {
        node.name: {
            target.id
            for inner in ast.walk(node)
            if isinstance(inner, ast.Assign)
            for target in inner.targets
            if isinstance(target, ast.Name)
            and isinstance(inner.value, ast.Call)
            and isinstance(inner.value.func, ast.Name)
            and inner.value.func.id
            in {"checked_path", "checked_read_tree", "_checked_network_source"}
        }
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


@pytest.mark.parametrize("server", sorted(GUARDED))
def test_every_path_taking_tool_checks_its_argument(server):
    if not (REPO / server).exists():
        pytest.skip(f"{server} not present")
    checked = _checked_arguments(server)
    for name, args in GUARDED[server].items():
        assert name in checked, f"{server}: {name} is gone"
        missing = set(args) - checked[name]
        assert not missing, f"{server}: {name} does not check {sorted(missing)}"



@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_read_tree_refuses_an_escaping_descendant(monkeypatch, tmp_path):
    root = tmp_path / "allowed"
    tree = root / "dataset"
    outside = tmp_path / "outside.csv"
    tree.mkdir(parents=True)
    outside.write_text("outside")
    (tree / "buses.csv").symlink_to(outside)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(root))

    with pytest.raises(PathNotAllowed, match="outside its allowed MCP root"):
        checked_read_tree(str(tree), purpose="dataset")


def test_staged_directory_write_preserves_unrelated_files(tmp_path):
    output = tmp_path / "tables"
    output.mkdir()
    (output / "keep.txt").write_text("keep")
    (output / "buses.csv").write_text("old")

    def write(staging):
        path = pathlib.Path(staging) / "buses.csv"
        path.write_text("new")
        return {"dir": staging, "files": [str(path)]}

    result = staged_directory_write(str(output), True, write)
    assert (output / "keep.txt").read_text() == "keep"
    assert (output / "buses.csv").read_text() == "new"
    assert result["dir"] == str(output)
    assert result["files"] == [str(output / "buses.csv")]


def test_psse_command_name_is_not_a_spec_path():
    result = psse_mcp.lookup_psspy_command("../../pyproject")
    assert result["status"] == "error"
    assert "ASCII Python identifier" in result["message"]


PSSE_PROHIBITED_COMMANDS = (
    "accc_ras",
    "accc_ras_2",
    "addconditionelement",
    "addcontingencyelement",
    "addmodellibrary",
    "addpythonconditionelement",
    "addpythoncontingencyelement",
    "addpythonremedialactionelement",
    "addremedialactionelement",
    "allow_pssuserpf",
    "append_ras",
    "dropmodellibrary",
    "dropmodelprogram",
    "getmodfunclist",
    "launch_program",
    "read_ras",
    "retry_pssuserpf",
    "runiplanfile",
    "runrspnsfile",
    "set_input_dev",
    "setdiagautofile",
    "user",
)


def test_psse_prohibited_command_contract_matches_the_server():
    assert set(PSSE_PROHIBITED_COMMANDS) == psse_mcp._PROHIBITED_PSSPY_COMMANDS


@pytest.mark.parametrize("command", PSSE_PROHIBITED_COMMANDS)
def test_psse_generic_dispatch_refuses_executable_commands_before_engine_start(
    monkeypatch, command
):
    engine_starts = []

    def unexpected_engine_start():
        engine_starts.append(command)
        raise AssertionError("PSS/E must not start for a prohibited command")

    monkeypatch.setattr(psse_mcp, "_ensure_psse", unexpected_engine_start)
    result = psse_mcp.run_psspy_command(command, {})

    assert result["status"] == "error"
    assert "not available through run_psspy_command" in result["message"]
    assert engine_starts == []


def test_psse_generic_dispatch_still_calls_permitted_command(monkeypatch):
    calls = []

    class FakePsspy:
        def nsol(self):
            calls.append("nsol")
            return 0

    fake_psspy = FakePsspy()
    monkeypatch.setattr(psse_mcp, "psspy", fake_psspy)
    monkeypatch.setattr(psse_mcp, "_ensure_psse", lambda: fake_psspy)

    result = psse_mcp.run_psspy_command("nsol", {})

    assert result["status"] == "success"
    assert result["_function"] == "nsol"
    assert calls == ["nsol"]


def test_psse_generic_file_arguments_use_the_shared_policy(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.snp"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))
    spec = psse_mcp.lookup_psspy_command("case")

    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        psse_mcp._guard_psspy_path_arguments(spec, {"sfile": str(outside)})


PSSE_PATH_CASES = (
    ("pp_accc_multi_case", "accfiles", True),
    ("accc_multiple_merge", "acfiles", True),
    ("accc_multiple_run_report", "acfiles", True),
    ("accc_multiple_run_report_2", "acfiles", True),
    ("runiplanfile", "iplname", False),
    ("runrspnsfile", "rspname", False),
    ("setdiagautofile", "autoname", False),
)


@pytest.mark.parametrize("command,parameter,is_array", PSSE_PATH_CASES)
@pytest.mark.parametrize("spelling", ["absolute", "traversal"])
def test_psse_audited_path_arguments_refuse_outside_roots(
    tmp_path, monkeypatch, command, parameter, is_array, spelling
):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))
    candidate = outside / "commands.idv"
    if spelling == "traversal":
        candidate = allowed / ".." / "outside" / "commands.idv"
    value = [str(candidate)] if is_array else str(candidate)
    spec = psse_mcp.lookup_psspy_command(command)

    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        psse_mcp._guard_psspy_path_arguments(spec, {parameter: value})


def test_psse_path_metadata_matches_the_bundled_specs():
    metadata = json.loads(psse_mcp.PATH_PARAMETER_METADATA.read_text())
    assert metadata["schema"] == 1
    for command, parameters in metadata["commands"].items():
        spec = psse_mcp.lookup_psspy_command(command)
        assert "status" not in spec, command
        spec_names = {parameter["name"] for parameter in spec["parameters"]}
        assert set(parameters) <= spec_names, command
        assert set(parameters.values()) <= {"path", "paths", "path-index-2"}


# A parameter name or description that mentions a file, path, directory or
# folder. Deliberately broad: every hit must be either guarded or recorded as
# reviewed, so regenerating the bundled specs cannot quietly unguard one.
PSSE_PATHISH_NAME = re.compile(
    r"(file|fname|path|folder|zip|csv|xml|iplname|rspname|autoname)", re.I
)
PSSE_PATHISH_DESCRIPTION = re.compile(
    r"\b(file|filename|path|pathname|directory|folder)\b", re.I
)


def test_psse_path_metadata_covers_every_pathish_spec_parameter():
    metadata = json.loads(psse_mcp.PATH_PARAMETER_METADATA.read_text())
    commands = metadata["commands"]
    reviewed = metadata["reviewed_non_paths"]
    undeclared = []
    for spec_file in sorted(psse_mcp.JSON_DIR.glob("*.json")):
        command = spec_file.stem
        if command == "_index":
            continue
        spec = json.loads(spec_file.read_text(encoding="utf-8"))
        declared = commands.get(command, {})
        excused = reviewed.get(command, [])
        for parameter in spec.get("parameters", []):
            name = str(parameter.get("name", ""))
            description = str(parameter.get("description", ""))
            if name in declared or name in excused:
                continue
            if PSSE_PATHISH_NAME.search(name) or PSSE_PATHISH_DESCRIPTION.search(
                description
            ):
                undeclared.append(f"{command}.{name}")
    assert not undeclared, (
        "path-carrying psspy parameters with no containment decision: "
        + ", ".join(undeclared)
    )


def test_psse_reviewed_non_paths_name_real_unguarded_parameters():
    metadata = json.loads(psse_mcp.PATH_PARAMETER_METADATA.read_text())
    for command, names in metadata["reviewed_non_paths"].items():
        spec = psse_mcp.lookup_psspy_command(command)
        assert "status" not in spec, command
        spec_names = {parameter["name"] for parameter in spec["parameters"]}
        assert set(names) <= spec_names, command
        assert not set(names) & set(metadata["commands"].get(command, {})), command


def test_psse_structured_module_path_checks_only_its_path_field(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))
    spec = psse_mcp.lookup_psspy_command("addconditionelement")

    with pytest.raises(PathNotAllowed, match="outside allowed MCP roots"):
        psse_mcp._guard_psspy_path_arguments(
            spec, {"elmtkey": ["module", "function", str(outside)]}
        )


def test_pslf_generated_outputs_use_the_shared_policy(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    working = tmp_path / "working"
    allowed.mkdir()
    working.mkdir()
    monkeypatch.chdir(working)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = pslf_mcp.save_case()
    assert result["status"] == "error unknown"
    assert "outside allowed MCP roots" in result["message"]
