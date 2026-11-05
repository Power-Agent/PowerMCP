"""Unit tests for powermcp.config (no real software required)."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

import pytest

from powermcp import config as cfg


def test_load_empty_when_no_file(isolated_config):
    assert cfg.load() == {}
    assert "no config yet" in cfg.show()


def test_set_and_get_roundtrip(isolated_config):
    cfg.set_value("psse", "version", "36.2")
    assert cfg.get("psse", "version") == "36.2"
    assert cfg.load()["psse"]["version"] == "36.2"
    assert "36.2" in cfg.show()


def test_windows_backslash_path_roundtrip(isolated_config):
    win = r"C:\Program Files\PTI\PSSE36\36.2\PSSPY311"
    cfg.set_value("psse", "python_lib", win)
    assert cfg.get("psse", "python_lib") == win


def test_get_path_unset_raises_actionable(isolated_config):
    with pytest.raises(cfg.ConfigError) as exc:
        cfg.get_path("pslf", "python_lib")
    msg = str(exc.value)
    assert "powermcp install" in msg
    assert "powermcp config set pslf.python_lib" in msg
    assert "POWERMCP_PSLF_PYTHON_LIB" in msg


def test_get_path_env_override_wins(isolated_config, tmp_path, monkeypatch):
    target = tmp_path / "ltspice.exe"
    target.write_text("")
    monkeypatch.setenv("POWERMCP_LTSPICE_EXE", str(target))
    assert cfg.get_path("ltspice", "exe") == str(target)


def test_get_path_config_value_used(isolated_config, tmp_path):
    target = tmp_path / "PSSPY311"
    target.mkdir()
    cfg.set_value("psse", "python_lib", str(target))
    assert cfg.get_path("psse", "python_lib") == str(target)


def test_get_path_missing_path_raises(isolated_config):
    cfg.set_value("psse", "bin", r"C:\does\not\exist\PSSBIN")
    with pytest.raises(cfg.ConfigError) as exc:
        cfg.get_path("psse", "bin")
    assert "does not exist" in str(exc.value)


def test_get_path_must_exist_false_skips_check(isolated_config):
    cfg.set_value("psse", "bin", r"C:\does\not\exist\PSSBIN")
    assert cfg.get_path("psse", "bin", must_exist=False).endswith("PSSBIN")


def test_get_path_falls_back_to_legacy_default(isolated_config, tmp_path, monkeypatch):
    from powermcp import registry

    existing = tmp_path / "legacy"
    existing.mkdir()
    monkeypatch.setattr(registry, "legacy_default", lambda t, k: str(existing))
    assert cfg.get_path("psse", "python_lib") == str(existing)


def _concurrent_config_writer(index: int, home: str) -> None:
    os.environ["POWERMCP_HOME"] = home
    cfg.set_value("worker", f"key_{index}", str(index))


def test_concurrent_process_updates_are_not_lost(isolated_config):
    context = multiprocessing.get_context("spawn")
    workers = 8
    processes = [
        context.Process(
            target=_concurrent_config_writer, args=(index, str(isolated_config))
        )
        for index in range(workers)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
    for process in processes:
        assert not process.is_alive(), "config writer hung waiting for lock"
        assert process.exitcode == 0
    config = cfg.load()
    assert config["worker"] == {f"key_{index}": str(index) for index in range(workers)}


def test_save_uses_unique_staging_file_and_cleans_up_on_failure(isolated_config, monkeypatch):
    def fail_replace(source, destination):
        assert Path(source).parent == cfg.config_dir()
        assert Path(source).name.startswith(".config.toml.")
        assert Path(source).suffix == ".tmp"
        raise OSError("simulated replace failure")

    monkeypatch.setattr(cfg.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        cfg.save({"one": {"value": "1"}})
    assert not cfg.config_path().exists()
    assert list(isolated_config.glob(".config.toml.*.tmp")) == []


def test_save_replaces_existing_file_atomically(isolated_config):
    cfg.save({"existing": {"keep": "yes"}})
    cfg.save({"existing": {"keep": "yes", "new": "value"}})
    assert cfg.load() == {"existing": {"keep": "yes", "new": "value"}}
    assert list(isolated_config.glob(".config.toml.*.tmp")) == []
