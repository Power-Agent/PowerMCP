"""Egret OPF must solve cases whose branches have no thermal rating (issue #128).

MATPOWER writes rateA = 0 for an unlimited branch. powerio leaves the Egret
rating keys out for those branches, and Egret's OPF models index them directly.
"""

import json
from pathlib import Path
import sys

import pytest

_CASE14 = Path(__file__).resolve().parents[1] / "Egret" / "pglib_opf_case14_ieee.m"


@pytest.fixture()
def egret_mcp(tmp_path, monkeypatch):
    pytest.importorskip("egret")
    monkeypatch.setenv("POWERMCP_HOME", str(tmp_path / "powermcp-home"))
    from powermcp.registry import TOOLS

    egret_dir = str(TOOLS["egret"].resolve_server_dir())
    if egret_dir not in sys.path:
        sys.path.insert(0, egret_dir)
    import egret_mcp as _egret_mcp

    return _egret_mcp


def _unrate_every_other_branch(target: Path) -> int:
    """Copy IEEE 14-bus with rateA/B/C = 0 on alternate branches; return how many."""
    head, rest = _CASE14.read_text().split("mpc.branch = [", 1)
    body, tail = rest.split("];", 1)
    rows = [row.split() for row in body.strip().splitlines()]
    for cols in rows[::2]:
        cols[5:8] = ["0", "0", "0"]
    table = "\n".join("\t" + "\t".join(cols) for cols in rows)
    target.write_text(f"{head}mpc.branch = [\n{table}\n];{tail}")
    return len(rows[::2])


def test_dc_opf_solves_case_with_unrated_branches(egret_mcp, tmp_path):
    pytest.importorskip("highspy")
    case = tmp_path / "case14_unrated.m"
    unrated = _unrate_every_other_branch(case)

    loaded = egret_mcp.load_model_from_any(str(case))
    assert loaded["status"] == "success", loaded

    solved = egret_mcp.solve_dc_opf(loaded["case_file"], solver="highs")

    assert solved["status"] == "success", solved
    branches = solved["solution"]["elements"]["branch"]
    assert sum(1 for b in branches.values() if b["rating_long_term"] is None) == unrated


def test_missing_rating_keys_read_as_unlimited(egret_mcp, tmp_path):
    case = tmp_path / "case.json"
    case.write_text(json.dumps({
        "elements": {"branch": {"1": {"from_bus": "1", "to_bus": "2"},
                                "2": {"from_bus": "2", "to_bus": "3", "rating_long_term": 100.0}}},
        "system": {"baseMVA": 100.0},
    }))

    branches = egret_mcp._read_model_data(str(case)).data["elements"]["branch"]

    assert branches["1"]["rating_long_term"] is None
    assert branches["1"]["rating_emergency"] is None
    assert branches["2"]["rating_long_term"] == 100.0
