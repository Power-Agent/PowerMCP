"""Regression test: the headless engine must reproduce the notebook run in baseline_uganda/.

Needs the (large, not versioned) Uganda inputs. Point ONSSET_UGANDA_REPO at the OnSSET
clone that holds them, otherwise the path recorded in inputs.json is used; skipped if absent.
Takes a few minutes.

OnSSET sizes PV hybrid mini-grids with scipy's differential_evolution without a seed, so
even two notebook runs differ slightly. Technology choice, population and connections are
compared exactly; capacity, investment and emissions within a tolerance.
"""
import json
import os
import sys

import pandas as pd
import pytest

pytest.importorskip("onsset")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import onsset_engine as eng  # noqa: E402

BASELINE = os.path.join(HERE, "baseline_uganda")
with open(os.path.join(BASELINE, "inputs.json")) as f:
    META = json.load(f)
REPO = os.environ.get("ONSSET_UGANDA_REPO", META["onsset_repo"])
INPUTS = {k: os.path.join(REPO, v["path"]) for k, v in META["inputs"].items()}
REFERENCE_RESULTS = os.path.join(REPO, "test/outputTestUganda", f"{META['scenario_name']}_Results.csv")

pytestmark = pytest.mark.skipif(not os.path.exists(INPUTS["input_csv"]), reason="Uganda inputs not available")


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    with open(os.path.join(BASELINE, "params.json")) as f:
        params = json.load(f)
    out = tmp_path_factory.mktemp("uganda")
    return eng.run(INPUTS["input_csv"], INPUTS["pv_csv"], INPUTS["wind_csv"], INPUTS["mv_lines"],
                   params, str(out), META["scenario_name"])


def test_summary_matches_notebook(result):
    expected = pd.read_csv(os.path.join(BASELINE, "expected_summary.csv"), index_col=0)
    expected.columns = [c.replace("(tCO2)", "(ktCO2)") for c in expected.columns]
    actual = pd.read_csv(result["files"]["summary"], index_col=0)
    assert list(actual.index) == list(expected.index)
    assert list(actual.columns) == list(expected.columns)
    exact = [c for c in expected.columns if c.startswith(("Population", "NewConnections"))]
    pd.testing.assert_frame_equal(actual[exact], expected[exact], check_dtype=False)
    approx = [c for c in expected.columns if c not in exact]
    pd.testing.assert_frame_equal(actual[approx], expected[approx], check_dtype=False, rtol=0.02, atol=0.05)


def test_full_electrification_reached(result):
    assert result["electrification_rate"][2050] == pytest.approx(1.0)


@pytest.mark.skipif(not os.path.exists(REFERENCE_RESULTS), reason="reference Results.csv not available")
def test_settlement_level_results_match(result):
    cols = ["id", "FinalElecCode2050", "Pop2050", "NewConnections2050", "InvestmentCost2050", "NewCapacity2050"]
    ref = pd.read_csv(REFERENCE_RESULTS, usecols=cols).set_index("id").sort_index()
    act = pd.read_csv(result["files"]["results"], usecols=cols).set_index("id").sort_index()
    exact = ["FinalElecCode2050", "Pop2050", "NewConnections2050"]
    pd.testing.assert_frame_equal(act[exact], ref[exact], check_dtype=False)
    # Per-settlement MV routing may shift with the stochastic mini-grid LCOE; totals per technology may not.
    totals = ["InvestmentCost2050", "NewCapacity2050"]
    pd.testing.assert_frame_equal(act.groupby("FinalElecCode2050")[totals].sum(),
                                  ref.groupby("FinalElecCode2050")[totals].sum(), rtol=0.02)
