"""Tests for the ANDES MCP server's simulation tools (power flow, time-domain,
and eigenvalue/small-signal analysis).

andes is an optional pip extra (`pip install "powermcp[andes]"`), not a core
dependency, so every test in this module goes through the `andes_mcp` fixture
in conftest.py, which calls `pytest.importorskip("andes")`. In this repo's
base CI job (.github/workflows/test.yml installs no extras), these tests
therefore show as SKIPPED, not run -- verified locally by installing andes
into a venv and running this file directly (`pip install andes && pytest
tests/test_andes_server.py -v`), matching the existing ANDES-bridge tests'
posture in test_powerio_server.py.

ANDES/kundur_full.json is the repo's only ANDES fixture: a Kundur two-area
four-machine system with its own embedded dynamic models (GENROU, exciters,
governors), so it exercises power flow, time-domain simulation, and
eigenvalue analysis all in one case with no fixture authoring needed here.

The raw+dyr dynamic-model-loading tests further down this file use ANDES's
own bundled ieee14 PSS/E case (raw + dyr), resolved via andes.get_case(...)
at test-call time -- see the comment above _ieee14_raw_dyr_paths() for why.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KUNDUR_FULL = Path(__file__).resolve().parents[1] / "ANDES" / "kundur_full.json"


def test_run_power_flow_converges(andes_mcp):
    r = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    assert r["power_flow"]["converged"] is True


def test_get_system_info_reports_plausible_counts(andes_mcp):
    # get_system_info reads from the module-level system_state, so this test
    # populates it itself rather than depending on the execution order of the
    # tests above.
    r = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert r["status"] == "success", r

    info = andes_mcp.get_system_info()
    assert info["status"] == "success", info
    assert info["num_buses"] > 0
    assert info["num_generators"] > 0


def test_run_time_domain_simulation_completes(andes_mcp):
    pf = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert pf["status"] == "success", pf

    r = andes_mcp.run_time_domain_simulation(step_size=0.01, t_end=1.0)
    assert r["status"] == "success", r
    sim = r["simulation"]
    assert sim["success"] is True
    assert sim["status"] == "completed"
    assert sim["t_end"] == 1.0
    assert sim["step_size"] == 0.01
    # Not asserting on t_array's shape here: this installed ANDES version
    # returns ss.dae.t as a 0-d array (final sim time) rather than a full
    # per-step series, which is a pre-existing quirk of
    # run_time_domain_simulation orthogonal to the eigenvalue-analysis fix
    # this PR targets, so it's left alone (out of scope).
    assert "t_array" in sim


def test_run_eigenvalue_analysis_returns_modes(andes_mcp):
    r = andes_mcp.run_eigenvalue_analysis(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    analysis = r["analysis"]
    assert analysis["success"] is True
    assert analysis["n_modes"] > 0

    modes = analysis["modes"]
    assert len(modes) == analysis["n_modes"]
    for mode in modes:
        assert isinstance(mode["frequency_hz"], (int, float))
        assert isinstance(mode["damping_ratio_pct"], (int, float))
        assert isinstance(mode["is_oscillatory"], bool)
        assert len(mode["eigenvalue"]) == 2

    # Regression check for the original bug: run_eigenvalue_analysis used to
    # read ss.EIG.vectors/state_desc, attributes that don't exist on the real
    # EIG object, so hasattr() guards silently returned [] for these fields.
    # The real attribute is x_name (state labels); it must be non-empty now.
    assert len(analysis["state_names"]) > 0
    assert len(analysis["participation_factors"]) > 0

    # Modes are sorted least-damped (most concerning) first.
    damping_values = [m["damping_ratio_pct"] for m in modes]
    assert damping_values == sorted(damping_values)


def test_eigenvalue_modes_keep_their_native_index(andes_mcp):
    """A sorted mode still has to be traceable to its participation column.

    `modes` is re-sorted by damping; `participation_factors`/`state_names`
    stay in ANDES's native ordering. `index` is what ties the two together,
    so it has to survive the sort and stay a valid row into the matrix.
    """
    r = andes_mcp.run_eigenvalue_analysis(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    analysis = r["analysis"]

    indices = [m["index"] for m in analysis["modes"]]
    # Every native position appears exactly once...
    assert sorted(indices) == list(range(analysis["n_modes"]))
    # ...and the sort actually moved something, so index != list position.
    assert indices != sorted(indices)
    assert len(analysis["participation_factors"]) >= analysis["n_modes"]


def test_eigenvalue_real_modes_report_full_damping(andes_mcp):
    """Real modes get +/-100% damping, matching ANDES's own report.

    Hardcoding 0.0 for them would sort a real positive eigenvalue --
    monotonic instability -- into the middle of the list instead of first.
    """
    r = andes_mcp.run_eigenvalue_analysis(str(KUNDUR_FULL))
    assert r["status"] == "success", r

    real_modes = [m for m in r["analysis"]["modes"] if not m["is_oscillatory"]]
    assert real_modes, "kundur_full has real modes; the assertion below needs one"
    for mode in real_modes:
        assert mode["frequency_hz"] == 0.0
        if mode["eigenvalue"] == [0.0, 0.0]:
            continue  # a mode at the origin has no defined damping ratio
        assert abs(mode["damping_ratio_pct"]) == pytest.approx(100.0)


def test_eigenvalue_keeps_pre_0_3_0_fields(andes_mcp):
    """`n_eigenvalues`/`eigenvalues` stay available to existing callers."""
    r = andes_mcp.run_eigenvalue_analysis(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    analysis = r["analysis"]

    assert analysis["n_eigenvalues"] == analysis["n_modes"]
    assert len(analysis["eigenvalues"]) == analysis["n_modes"]


def test_run_eigenvalue_analysis_missing_file(andes_mcp, tmp_path):
    r = andes_mcp.run_eigenvalue_analysis(str(tmp_path / "nope.json"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


# ---------------------------------------------------------------------------
# PSS/E raw+dyr dynamic-model loading (fungible-farm/PowerMCP#2)
#
# These tests use ANDES's own bundled ieee14 example case (raw + dyr),
# resolved at test-call time via andes.get_case(...), which reads from the
# installed andes package's own andes/cases/ directory (andes declares these
# as package-data in its own pyproject.toml). No .raw/.dyr fixture is
# authored or vendored into this repo: ieee14.raw/.dyr are GPL-3.0 ANDES
# files, and this repo is MIT, so referencing the installed dependency's own
# copy avoids any vendoring question entirely.
#
# andes must not be imported at module scope (it may not be installed), so
# the get_case() calls happen inside a helper invoked from within each test
# body, after the andes_mcp fixture parameter has already run
# pytest.importorskip("andes").
# ---------------------------------------------------------------------------


def _ieee14_raw_dyr_paths():
    import andes

    raw_path = andes.get_case("ieee14/ieee14.raw")
    dyr_path = andes.get_case("ieee14/ieee14.dyr")
    return raw_path, dyr_path


def test_dynamic_models_loaded_reflects_the_system_not_the_argument(andes_mcp):
    """kundur_full.json embeds its own dynamics and takes no `.dyr`.

    The flag reports what actually attached, so it is True here even though
    `dyr_path` was never passed.
    """
    r = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    pf = r["power_flow"]
    assert pf["n_dynamic_generators"] > 0
    assert pf["dynamic_models_loaded"] is True


def test_run_power_flow_without_dyr_has_no_dynamic_models(andes_mcp):
    raw_path, _ = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path)
    assert r["status"] == "success", r
    pf = r["power_flow"]
    assert pf["converged"] is True
    assert pf["dynamic_models_loaded"] is False
    assert pf["n_dynamic_generators"] == 0


def test_run_power_flow_with_dyr_attaches_dynamic_models(andes_mcp):
    raw_path, dyr_path = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path, dyr_path=dyr_path)
    assert r["status"] == "success", r
    pf = r["power_flow"]
    assert pf["converged"] is True
    assert pf["dynamic_models_loaded"] is True
    # Not asserting an exact count (e.g. == 5): stay robust to upstream ANDES
    # case-file changes across versions -- only assert that dynamics
    # actually attached.
    assert pf["n_dynamic_generators"] > 0


def test_run_power_flow_with_dyr_enables_time_domain_simulation(andes_mcp):
    # The actual motivating scenario from the issue: without a .dyr there are
    # no real dynamics to simulate.
    raw_path, dyr_path = _ieee14_raw_dyr_paths()

    pf = andes_mcp.run_power_flow(raw_path, dyr_path=dyr_path)
    assert pf["status"] == "success", pf
    assert pf["power_flow"]["n_dynamic_generators"] > 0

    r = andes_mcp.run_time_domain_simulation(step_size=0.01, t_end=1.0)
    assert r["status"] == "success", r
    sim = r["simulation"]
    assert sim["success"] is True
    assert sim["status"] == "completed"


def test_run_power_flow_missing_dyr_file(andes_mcp, tmp_path):
    raw_path, _ = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path, dyr_path=str(tmp_path / "nope.dyr"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()
