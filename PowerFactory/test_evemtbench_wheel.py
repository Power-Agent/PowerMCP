"""Smoke-test EvEMTBench catalog files from an installed PowerMCP wheel.

Run this script from outside the source checkout after installing the wheel.
It intentionally avoids importing or launching licensed PowerFactory software.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

CATALOGS = {
    "evemtbench_transformers.json": {10, 11, 12},
    "evemtbench_overhead_lines.json": {3, 7, 9},
    "evemtbench_underground_cables.json": {3, 6},
    "evemtbench_external_grids.json": {4},
    "evemtbench_loads.json": {5},
    "evemtbench_synchronous_machines.json": {13},
}

spec = importlib.util.find_spec("powermcp")
if spec is None or not spec.submodule_search_locations:
    raise SystemExit("powermcp is not importable from the installed wheel")
package_root = Path(next(iter(spec.submodule_search_locations)))
catalog_root = package_root / "_servers" / "PowerFactory" / "data"

identifiers = set()
for filename, expected_tables in CATALOGS.items():
    path = catalog_root / filename
    if not path.is_file():
        raise SystemExit(f"wheel is missing catalog: {path}")
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot load {filename}: {exc}") from exc
    if catalog.get("schema_version") != 1:
        raise SystemExit(f"{filename}: unsupported schema_version")
    catalog_id = catalog.get("catalog_id")
    if not isinstance(catalog_id, str) or not catalog_id:
        raise SystemExit(f"{filename}: missing catalog_id")
    if catalog_id in identifiers:
        raise SystemExit(f"duplicate catalog_id: {catalog_id}")
    identifiers.add(catalog_id)
    source = catalog.get("source", {})
    if not expected_tables.issubset(set(source.get("tables", []))):
        raise SystemExit(f"{filename}: source table metadata is incomplete")
    if not isinstance(catalog.get("classes"), dict) or not catalog["classes"]:
        raise SystemExit(f"{filename}: missing component classes")

print(f"Wheel catalog smoke test passed: {len(CATALOGS)} catalogs loaded from {catalog_root}")
