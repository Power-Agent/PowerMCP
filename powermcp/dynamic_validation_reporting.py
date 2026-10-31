"""Deterministic JSON and Markdown serialization for dynamic comparisons."""
from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any, Mapping

from .dynamic_validation import DynamicComparisonReport, DynamicSnapshot


def build_dynamic_validation_artifact(
    left: DynamicSnapshot,
    right: DynamicSnapshot,
    report: DynamicComparisonReport,
    *,
    comparison_settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a provenance-bearing, JSON-safe validation artifact."""
    if not isinstance(left, DynamicSnapshot) or not isinstance(right, DynamicSnapshot):
        raise TypeError("left and right must be DynamicSnapshot instances")
    if not isinstance(report, DynamicComparisonReport):
        raise TypeError("report must be a DynamicComparisonReport")
    if (left.case_id, left.study_type, left.disturbance_id) != (
        right.case_id, right.study_type, right.disturbance_id
    ):
        raise ValueError("snapshots do not describe the same study")
    return {
        "schema_version": 1,
        "study": {
            "case_id": left.case_id,
            "study_type": left.study_type,
            "disturbance_id": left.disturbance_id,
            "left_event_time_s": left.event_time_s,
            "right_event_time_s": right.event_time_s,
        },
        "engines": {
            "left": left.engine,
            "right": right.engine,
        },
        "run_metadata": {
            "left": {
                "engine_version": left.engine_version,
                "simulation_settings": dict(left.simulation_settings or {}),
            },
            "right": {
                "engine_version": right.engine_version,
                "simulation_settings": dict(right.simulation_settings or {}),
            },
        },
        "comparison_settings": dict(comparison_settings or {}),
        "result": {
            "passed": report.passed,
            "channels_compared": [asdict(item) for item in report.channels_compared],
            "missing_from_left": list(report.missing_from_left),
            "missing_from_right": list(report.missing_from_right),
            "unit_mismatches": list(report.unit_mismatches),
            "insufficient_overlap": list(report.insufficient_overlap),
            "outside_tolerance": list(report.outside_tolerance),
        },
    }


def dynamic_validation_json(artifact: Mapping[str, Any]) -> str:
    """Serialize an artifact deterministically (stable keys and whitespace)."""
    return json.dumps(artifact, sort_keys=True, indent=2, allow_nan=False) + "\n"


def dynamic_validation_markdown(artifact: Mapping[str, Any]) -> str:
    """Render a concise human-readable report from the same artifact data."""
    study = artifact["study"]
    engines = artifact["engines"]
    result = artifact["result"]
    status = "PASS" if result["passed"] else "FAIL"
    lines = [
        "# Cross-engine transient validation",
        "",
        f"**Result:** {status}",
        "",
        "## Study provenance",
        "",
        f"- Case: `{study['case_id']}`",
        f"- Study: `{study['study_type']}`",
        f"- Disturbance: `{study['disturbance_id']}`",
        f"- Engines: `{engines['left']}` vs `{engines['right']}`",
        f"- Event origins (s): {study['left_event_time_s']} vs {study['right_event_time_s']}",
        f"- Engine versions: {artifact['run_metadata']['left']['engine_version'] or 'not supplied'} vs {artifact['run_metadata']['right']['engine_version'] or 'not supplied'}",
        f"- Run settings: {json.dumps(artifact['run_metadata'], sort_keys=True)}",
        "",
        "## Channel metrics",
        "",
        "| Channel | Unit | Samples | MAE | RMSE | Max error | IAE | Within tolerance |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for item in result["channels_compared"]:
        lines.append(
            f"| {item['channel']} | {item['unit']} | {item['samples_compared']} "
            f"| {item['mean_absolute_error']:.8g} "
            f"| {item['root_mean_square_error']:.8g} "
            f"| {item['maximum_absolute_error']:.8g} "
            f"| {item['integrated_absolute_error']:.8g} "
            f"| {'yes' if item['within_tolerance'] else 'no'} |"
        )
    for key, label in (
        ("missing_from_left", "Missing from left"),
        ("missing_from_right", "Missing from right"),
        ("unit_mismatches", "Unit mismatches"),
        ("insufficient_overlap", "Insufficient overlap"),
        ("outside_tolerance", "Outside tolerance"),
    ):
        values = result[key]
        if values:
            lines.extend(["", f"## {label}", "", *[f"- `{value}`" for value in values]])
    lines.append("")
    return "\n".join(lines)
