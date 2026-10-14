""""Unit tests for ConnectorBench's safe, read-only MCP catalog checks."""
from __future__ import annotations

from connectorbench import inspect_tool_contracts


def _tool(name="solve", schema=None, description="Run a solver"):
    return {
        "name": name,
        "description": description,
        "inputSchema": schema if schema is not None else {
            "type": "object",
            "properties": {"case": {"type": "string"}},
            "required": ["case"],
        },
    }


def test_valid_catalog_passes_and_is_json_serializable():
    report = inspect_tool_contracts([_tool(), _tool("inspect", {"type": "object"})])

    assert report["passed"] is True
    assert report["tool_count"] == 2
    assert report["errors"] == []
    assert report["tools"][0]["required_count"] == 1


def test_tool_name_at_128_character_limit_is_accepted():
    report = inspect_tool_contracts([_tool(name="a" * 128)])

    assert report["passed"] is True
    assert report["errors"] == []


def test_tool_name_over_128_characters_is_rejected():
    report = inspect_tool_contracts([_tool(name="a" * 129)])

    assert report["passed"] is False
    assert any(item["code"] == "invalid_name_length" for item in report["errors"])


def test_tool_name_with_non_ascii_or_slash_is_rejected_by_strict_policy():
    report = inspect_tool_contracts([_tool(name="café"), _tool(name="server/tool")])

    assert report["passed"] is False
    assert sum(item["code"] == "invalid_name" for item in report["errors"]) == 2


def test_duplicate_tool_names_are_reported():
    report = inspect_tool_contracts([_tool(), _tool()])

    assert report["passed"] is False
    assert any(item["code"] == "duplicate_name" for item in report["errors"])
    # Duplicate registration is a catalog error, not a schema error.
    assert all(item["schema_valid"] for item in report["tools"])


def test_required_properties_can_be_defined_by_composed_schema():
    report = inspect_tool_contracts([
        _tool(schema={
            "type": "object",
            "allOf": [{"properties": {"bus_id": {"type": "string"}}}],
            "required": ["bus_id"],
        })
    ])

    assert report["passed"] is True
    assert report["errors"] == []


def test_schema_root_must_be_an_object():
    report = inspect_tool_contracts([_tool(schema={"type": "array"})])

    assert report["passed"] is False
    assert any(item["code"] == "invalid_schema_root_type" for item in report["errors"])


def test_missing_description_is_a_warning_not_a_failure():
    report = inspect_tool_contracts([_tool(description="  ")])

    assert report["passed"] is True
    assert report["errors"] == []
    assert any(item["code"] == "missing_description" for item in report["warnings"])


def test_non_json_values_are_rejected():
    report = inspect_tool_contracts([
        _tool(schema={"type": "object", "properties": {"value": {"default": float("nan")}}})
    ])

    assert report["passed"] is False
    assert any(item["code"] == "non_json_schema" for item in report["errors"])


def test_tool_without_input_schema_fails_closed():
    report = inspect_tool_contracts([{"name": "solve", "description": "Run a solver"}])

    assert report["passed"] is False
    assert any(item["code"] == "invalid_input_schema" for item in report["errors"])
