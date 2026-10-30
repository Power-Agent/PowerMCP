from __future__ import annotations

import os
from typing import Callable


_POWERMCP_HOPE_PATHS = {
    "HOPE_REPO_ROOT": "repo_root",
    "HOPE_JULIA_BIN": "julia_bin",
    "JULIA_DEPOT_PATH": "julia_depot_path",
}


def apply_powermcp_hope_config() -> dict[str, str]:
    """Expose PowerMCP's HOPE paths through the standalone server contract.

    Explicit runtime environment variables always win. Import and lookup
    failures are intentionally ignored so the vendored HOPE server remains
    runnable directly without importing the PowerMCP distribution.
    """
    try:
        from powermcp.config import get_path
    except Exception:
        return {}

    applied: dict[str, str] = {}
    lookup: Callable[..., str] = get_path
    for env_var, config_key in _POWERMCP_HOPE_PATHS.items():
        if os.environ.get(env_var):
            continue
        try:
            value = lookup("hope", config_key, must_exist=False)
        except Exception:
            continue
        if value:
            os.environ[env_var] = str(value)
            applied[env_var] = str(value)
    return applied
