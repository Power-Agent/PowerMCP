"""Tier-2 tests for the MCP client-config writers (no real clients needed)."""

from __future__ import annotations

import json
import sys

from powermcp.clients import _common, claude_code, claude_desktop, codex, configure


def test_server_entry_uses_absolute_interpreter():
    entry = _common.server_entry("psse")
    assert entry["command"] == sys.executable
    assert entry["args"] == ["-m", "powermcp", "run", "psse"]
    typed = _common.server_entry("psse", include_type=True)
    assert typed["type"] == "stdio"


def test_merge_preserves_foreign_and_prunes_managed():
    existing = {
        "mcpServers": {
            "filesystem": {"command": "npx", "args": ["-y", "server-filesystem"]},
            "powermcp_andes": {"command": "old", "args": ["x"]},  # managed but will be deselected
        },
        "otherTopLevelKey": {"keep": True},
    }
    merged = _common.merge_mcp_servers(existing, ["pandapower", "pypsa"], include_type=False)
    servers = merged["mcpServers"]
    assert "filesystem" in servers  # foreign preserved
    assert "powermcp_andes" not in servers  # stale managed pruned
    assert "powermcp_pandapower" in servers and "powermcp_pypsa" in servers
    assert merged["otherTopLevelKey"] == {"keep": True}  # other keys untouched
    # idempotent
    assert _common.merge_mcp_servers(merged, ["pandapower", "pypsa"], include_type=False) == merged


def test_write_json_config_backup_and_roundtrip(tmp_path):
    path = tmp_path / "claude_desktop_config.json"
    path.write_text(json.dumps({"mcpServers": {"filesystem": {"command": "npx", "args": []}}}), encoding="utf-8")
    out = _common.write_json_config(path, ["pandapower"], include_type=False, dry_run=False)
    assert out == str(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "filesystem" in data["mcpServers"]
    assert "powermcp_pandapower" in data["mcpServers"]
    # a one-time backup was created
    assert (tmp_path / "claude_desktop_config.json.powermcp.bak").exists()
    # second write is idempotent and does not create a second backup variant
    _common.write_json_config(path, ["pandapower"], include_type=False, dry_run=False)
    assert json.loads(path.read_text(encoding="utf-8")) == data


def test_write_json_config_dry_run_writes_nothing(tmp_path, capsys):
    path = tmp_path / "cfg.json"
    out = _common.write_json_config(path, ["pandapower"], include_type=True, dry_run=True)
    assert out is None
    assert not path.exists()
    assert "powermcp_pandapower" in capsys.readouterr().out


def test_codex_build_doc_preserves_comments_tables_and_prunes():
    existing = (
        '# my codex config\n'
        'model = "gpt-5"\n\n'
        '[mcp_servers.other]\n'
        'command = "node"\n'
        'args = ["server.js"]\n\n'
        '[mcp_servers.powermcp_stale]\n'
        'command = "x"\n'
        'args = ["y"]\n'
    )
    import tomlkit

    doc = codex._build_doc(existing, ["pandapower"])
    out = tomlkit.dumps(doc)
    assert "# my codex config" in out
    assert 'model = "gpt-5"' in out
    assert "[mcp_servers.other]" in out  # foreign server preserved
    assert "powermcp_stale" not in out  # stale managed pruned
    assert "[mcp_servers.powermcp_pandapower]" in out


def test_configure_dispatch_writes_all_three(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_desktop, "config_path", lambda: tmp_path / "desktop.json")
    monkeypatch.setattr(claude_code, "config_path", lambda: tmp_path / "claude.json")
    monkeypatch.setattr(codex, "config_path", lambda: tmp_path / "codex.toml")
    results = configure(["claude-desktop", "claude-code", "codex"], ["pandapower"], dry_run=False)
    assert set(results) == {"claude-desktop", "claude-code", "codex"}
    desktop = json.loads((tmp_path / "desktop.json").read_text(encoding="utf-8"))
    assert "powermcp_pandapower" in desktop["mcpServers"]
    claude = json.loads((tmp_path / "claude.json").read_text(encoding="utf-8"))
    assert claude["mcpServers"]["powermcp_pandapower"]["type"] == "stdio"
    assert "powermcp_pandapower" in (tmp_path / "codex.toml").read_text(encoding="utf-8")
