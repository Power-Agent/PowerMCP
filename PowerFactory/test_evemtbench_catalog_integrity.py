"""Cross-catalog invariants for the packaged EvEMTBench source data."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest


DATA_DIR = Path(__file__).parent / "data"
CATALOGS = {
    "evemtbench_transformers.json": {10, 11, 12},
    "evemtbench_overhead_lines.json": {3, 7, 9},
    "evemtbench_underground_cables.json": {3, 6},
    "evemtbench_external_grids.json": {4},
    "evemtbench_loads.json": {5},
    "evemtbench_synchronous_machines.json": {13},
}


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_catalog(catalog: dict, expected_tables: set[int]) -> None:
    """Validate shared metadata and numeric range invariants without PowerFactory."""
    if catalog.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    catalog_id = catalog.get("catalog_id")
    if not isinstance(catalog_id, str) or not catalog_id.strip():
        raise ValueError("catalog_id must be a non-empty string")

    source = catalog.get("source")
    if not isinstance(source, dict) or not isinstance(source.get("title"), str):
        raise ValueError("source.title is required")
    tables = source.get("tables")
    if (
        not isinstance(tables, list)
        or not tables
        or any(isinstance(table, bool) or not isinstance(table, int) for table in tables)
    ):
        raise ValueError("source.tables must be a non-empty list of integers")
    if not expected_tables.issubset(set(tables)):
        raise ValueError(f"source.tables must include {sorted(expected_tables)}")
    if not isinstance(catalog.get("affiliation"), str) or not catalog["affiliation"].strip():
        raise ValueError("affiliation must be a non-empty string")

    classes = catalog.get("classes")
    if not isinstance(classes, dict) or not classes:
        raise ValueError("classes must be a non-empty object")

    # Voltage classes must not duplicate one another within a catalog, including
    # catalogs whose single class contains multiple supported nominal voltages.
    seen_voltages = set()
    seen_transformer_voltage_pairs = set()
    for class_name, item in classes.items():
        if not isinstance(item, dict):
            raise ValueError(f"class {class_name} must be an object")
        if "high_voltage_kv" in item or "low_voltage_kv" in item:
            if "high_voltage_kv" not in item or "low_voltage_kv" not in item:
                raise ValueError(
                    f"transformer class {class_name} must define both high and low voltage"
                )
            high_voltage = item["high_voltage_kv"]
            low_voltage = item["low_voltage_kv"]
            if (
                not _finite_number(high_voltage)
                or not _finite_number(low_voltage)
                or float(high_voltage) <= 0
                or float(low_voltage) <= 0
            ):
                raise ValueError(f"invalid transformer voltage pair in class {class_name}")
            pair = (float(high_voltage), float(low_voltage))
            if pair in seen_transformer_voltage_pairs:
                raise ValueError(f"duplicate transformer voltage pair: {pair}")
            seen_transformer_voltage_pairs.add(pair)

        raw_voltages = item.get("nominal_voltages_kv")
        if raw_voltages is None and "nominal_voltage_kv" in item:
            raw_voltages = [item["nominal_voltage_kv"]]
        if raw_voltages is not None:
            if not isinstance(raw_voltages, list):
                raise ValueError(f"voltage metadata for {class_name} must be a list")
            for raw_voltage in raw_voltages:
                if not _finite_number(raw_voltage) or float(raw_voltage) <= 0:
                    raise ValueError(f"invalid nominal voltage in class {class_name}")
                voltage = float(raw_voltage)
                if voltage in seen_voltages:
                    raise ValueError(f"duplicate nominal voltage: {voltage:g}")
                seen_voltages.add(voltage)

    # Validate every explicit closed numeric interval wherever it appears,
    # including nested catalog-only metadata. Other dependency expressions are
    # intentionally left as source metadata rather than interpreted here.
    def walk(value: object, path: str) -> None:
        if isinstance(value, dict):
            if "min_formula" in value:
                if "max" not in value:
                    raise ValueError(f"{path} must define both min_formula and max bounds")
                if (
                    not isinstance(value["min_formula"], str)
                    or not value["min_formula"].strip()
                    or not _finite_number(value["max"])
                ):
                    raise ValueError(f"{path} has invalid formula range bounds")
            elif "maximum" in value:
                if "min" not in value:
                    raise ValueError(f"{path} must define both min and maximum bounds")
                if not _finite_number(value["min"]):
                    raise ValueError(f"{path} has a non-finite or non-numeric minimum")
                maximum = value["maximum"]
                if isinstance(maximum, str):
                    if not maximum.strip():
                        raise ValueError(f"{path}.maximum must not be empty")
                elif not _finite_number(maximum):
                    raise ValueError(f"{path} has an invalid maximum")
                elif float(value["min"]) > float(maximum):
                    raise ValueError(f"{path} has reversed bounds")
            elif "min" in value or "max" in value:
                if "min" not in value or "max" not in value:
                    raise ValueError(f"{path} must define both min and max bounds")
                low, high = value["min"], value["max"]
                if not _finite_number(low) or not _finite_number(high):
                    raise ValueError(f"{path} has non-finite or non-numeric bounds")
                if float(low) > float(high):
                    raise ValueError(f"{path} has reversed bounds")
            if set(value) == {"value"} and not _finite_number(value["value"]):
                raise ValueError(f"{path}.value must be finite and numeric")
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(catalog, "catalog")

    powerfactory = catalog.get("powerfactory")
    if not isinstance(powerfactory, dict):
        raise ValueError("powerfactory metadata is required")
    mapped = powerfactory.get("mapped_attributes")
    if mapped is not None and (
        not isinstance(mapped, dict) or not mapped
        or any(not isinstance(key, str) or not isinstance(value, str)
               or not key.strip() or not value.strip()
               for key, value in mapped.items())
    ):
        raise ValueError("powerfactory.mapped_attributes must contain non-empty strings")

    # Line/cable capacitance conversions are safety-critical: these catalogs
    # must carry all unit and conversion fields, not merely validate them when
    # an optional marker happens to be present.
    if expected_tables in ({3, 7, 9}, {3, 6}):
        required_capacitance_fields = {
            "source_capacitance_unit",
            "powerfactory_capacitance_unit",
            "capacitance_conversion_factor",
        }
        missing = required_capacitance_fields - set(powerfactory)
        if missing:
            raise ValueError(
                "capacitance units/conversion metadata is missing: "
                + ", ".join(sorted(missing))
            )
        if (
            powerfactory.get("source_capacitance_unit") != "nF/km"
            or powerfactory.get("powerfactory_capacitance_unit") != "uF/km"
            or not _finite_number(powerfactory.get("capacitance_conversion_factor"))
            or not math.isclose(
                float(powerfactory["capacitance_conversion_factor"]),
                0.001,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError("capacitance units/conversion metadata is inconsistent")


@pytest.mark.parametrize("filename,expected_tables", CATALOGS.items())
def test_catalog_metadata_ranges_and_units_are_consistent(filename, expected_tables):
    catalog = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    validate_catalog(catalog, expected_tables)


def test_catalog_identifiers_are_unique():
    identifiers = [
        json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))["catalog_id"]
        for filename in CATALOGS
    ]
    assert len(identifiers) == len(set(identifiers))


def test_validator_rejects_reversed_and_non_finite_ranges():
    catalog = json.loads(
        (DATA_DIR / "evemtbench_loads.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(catalog)
    broken["classes"]["110"]["active_power_mw"] = {"min": 31.0, "max": 0.0}
    with pytest.raises(ValueError, match="reversed bounds"):
        validate_catalog(broken, {5})

    broken = copy.deepcopy(catalog)
    broken["classes"]["110"]["active_power_mw"] = {"min": 0.0, "max": float("inf")}
    with pytest.raises(ValueError, match="non-finite"):
        validate_catalog(broken, {5})


def test_validator_rejects_duplicate_nominal_voltage_classes():
    catalog = json.loads(
        (DATA_DIR / "evemtbench_external_grids.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(catalog)
    broken["classes"]["duplicate"] = copy.deepcopy(broken["classes"]["110"])
    with pytest.raises(ValueError, match="duplicate nominal voltage"):
        validate_catalog(broken, {4})



def test_validator_rejects_range_with_missing_bound():
    catalog = json.loads(
        (DATA_DIR / "evemtbench_loads.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(catalog)
    broken["classes"]["110"]["active_power_mw"].pop("max")
    with pytest.raises(ValueError, match="both min and max"):
        validate_catalog(broken, {5})


@pytest.mark.parametrize(
    "filename,expected_tables",
    [
        ("evemtbench_overhead_lines.json", {3, 7, 9}),
        ("evemtbench_underground_cables.json", {3, 6}),
    ],
)
def test_validator_rejects_missing_capacitance_metadata(filename, expected_tables):
    catalog = json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))
    broken = copy.deepcopy(catalog)
    broken["powerfactory"].pop("source_capacitance_unit")
    broken["powerfactory"].pop("powerfactory_capacitance_unit")
    broken["powerfactory"].pop("capacitance_conversion_factor")
    with pytest.raises(ValueError, match="capacitance units/conversion metadata is missing"):
        validate_catalog(broken, expected_tables)


def test_validator_rejects_duplicate_transformer_voltage_pair():
    catalog = json.loads(
        (DATA_DIR / "evemtbench_transformers.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(catalog)
    existing_class = next(iter(broken["classes"]))
    broken["classes"]["duplicate-pair"] = copy.deepcopy(
        broken["classes"][existing_class]
    )
    with pytest.raises(ValueError, match="duplicate transformer voltage pair"):
        validate_catalog(broken, {10, 11, 12})



def test_validator_rejects_incomplete_formula_range():
    catalog = json.loads(
        (DATA_DIR / "evemtbench_underground_cables.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(catalog)
    broken["construction"]["flat_phase_spacing_m"].pop("max")
    with pytest.raises(ValueError, match="both min_formula and max"):
        validate_catalog(broken, {3, 6})

    broken = copy.deepcopy(catalog)
    broken["construction"]["flat_phase_spacing_m"].pop("min_formula")
    with pytest.raises(ValueError, match="both min and max"):
        validate_catalog(broken, {3, 6})
