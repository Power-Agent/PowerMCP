"""run_contingency_analysis must work with current pandapower (issue #127).

pandapowerNet has no ``deepcopy`` method, so every call failed before the tool
switched to ``copy.deepcopy``.
"""

import importlib.util
from pathlib import Path
import sys

import pandapower.networks as pn

_SERVER_PATH = Path(__file__).resolve().parents[1] / "pandapower" / "panda_mcp.py"


def _load_server_like_runner():
    # The runner puts only the server's own directory on sys.path.
    server_dir = str(_SERVER_PATH.parent)
    sys.path.insert(0, server_dir)
    try:
        spec = importlib.util.spec_from_file_location("powermcp_pandapower_server_contingency", _SERVER_PATH)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(server_dir)


def test_n1_contingency_runs_on_case14_and_leaves_the_network_untouched(monkeypatch):
    server = _load_server_like_runner()
    net = pn.case14()
    monkeypatch.setattr(server, "_current_net", net)

    result = server.run_contingency_analysis()

    assert result["status"] == "success", result
    assert len(result["results"]) == len(net.line) + len(net.trafo)
    assert any(r["converged"] for r in result["results"])
    assert net.line.in_service.all() and net.trafo.in_service.all()
