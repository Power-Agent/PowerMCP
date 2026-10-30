from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from hope_mcp_server.powermcp_adapter import apply_powermcp_hope_config  # noqa: E402


class PowerMCPHopeAdapterTests(unittest.TestCase):
    def _fake_modules(self, values: dict[str, str]) -> dict[str, types.ModuleType]:
        package = types.ModuleType("powermcp")
        config = types.ModuleType("powermcp.config")

        def get_path(tool: str, key: str, *, must_exist: bool = True) -> str:
            self.assertEqual(tool, "hope")
            self.assertFalse(must_exist)
            if key not in values:
                raise RuntimeError("not configured")
            return values[key]

        config.get_path = get_path  # type: ignore[attr-defined]
        package.config = config  # type: ignore[attr-defined]
        return {"powermcp": package, "powermcp.config": config}

    def test_applies_configured_paths_when_runtime_environment_is_unset(self) -> None:
        values = {
            "repo_root": "C:/src/HOPE",
            "julia_bin": "C:/Julia/bin/julia.exe",
            "julia_depot_path": "D:/julia_depot",
        }
        with (
            mock.patch.dict(sys.modules, self._fake_modules(values)),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            applied = apply_powermcp_hope_config()
            self.assertEqual(os.environ["HOPE_REPO_ROOT"], values["repo_root"])
            self.assertEqual(os.environ["HOPE_JULIA_BIN"], values["julia_bin"])
            self.assertEqual(os.environ["JULIA_DEPOT_PATH"], values["julia_depot_path"])
            self.assertEqual(set(applied), {"HOPE_REPO_ROOT", "HOPE_JULIA_BIN", "JULIA_DEPOT_PATH"})

    def test_explicit_runtime_environment_takes_precedence(self) -> None:
        values = {
            "repo_root": "C:/configured/HOPE",
            "julia_bin": "C:/configured/julia.exe",
            "julia_depot_path": "D:/configured/depot",
        }
        explicit = {
            "HOPE_REPO_ROOT": "C:/explicit/HOPE",
            "HOPE_JULIA_BIN": "C:/explicit/julia.exe",
            "JULIA_DEPOT_PATH": "D:/explicit/depot",
        }
        with (
            mock.patch.dict(sys.modules, self._fake_modules(values)),
            mock.patch.dict(os.environ, explicit, clear=True),
        ):
            applied = apply_powermcp_hope_config()
            self.assertEqual(applied, {})
            for key, value in explicit.items():
                self.assertEqual(os.environ[key], value)

    def test_missing_optional_setting_does_not_break_standalone_server(self) -> None:
        with (
            mock.patch.dict(sys.modules, self._fake_modules({"repo_root": "C:/src/HOPE"})),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            applied = apply_powermcp_hope_config()
            self.assertEqual(applied, {"HOPE_REPO_ROOT": "C:/src/HOPE"})
            self.assertNotIn("JULIA_DEPOT_PATH", os.environ)


if __name__ == "__main__":
    unittest.main()
