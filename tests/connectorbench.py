"""Reusable, dependency-light conformance checks for MCP tool catalogs.

ConnectorBench validates the contract exposed by a server's list_tools result.
It intentionally does not invoke tools: inspection must be safe for connectors
whose calls can mutate a model, launch a solver, or consume a commercial license.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _field(value: Any, name: str, default: Any = None) -> Any:
    """Read an MCP model field from either an object or a plain mapping."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def inspect_tool_contracts(tools: Sequence[Any]) -> dict[str, Any]:
    """Inspect an MCP tool catalog and return a stable JSON-serializable report.

    Errors indicate malformed or ambiguous contracts. Missing descriptions are
    warnings because MCP permits them, but they reduce discoverability.
    No connector tool is called and no optional engine is imported here.
    """
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    seen: set[str] = set()
    catalog: list[dict[str, Any]] = []

    def issue(target: str, code: str, message: str, *, warning: bool = False) -> None:
        item = {"target": target, "code": code, "message": message}
        (warnings if warning else errors).append(item)

    for index, tool in enumerate(tools):
        name = _field(tool, "name")
        target = name if isinstance(name, str) and name else f"tools[{index}]"

        if not isinstance(name, str) or not name.strip():
            issue(target, "invalid_name", "Tool name must be a non-empty string.")
        elif not _NAME.fullmatch(name):
            issue(target, "invalid_name", "Tool name may contain only letters, digits, '.', '_' and '-'.")
        elif name in seen:
            issue(target, "duplicate_name", f"Tool name {name!r} is registered more than once.")
        else:
            seen.add(name)

        description = _field(tool, "description")
        if not isinstance(description, str) or not description.strip():
            issue(
                target,
                "missing_description",
                "Tool has no non-empty description; agents may struggle to discover its purpose.",
                warning=True,
            )

        schema = _field(tool, "inputSchema", _field(tool, "input_schema"))
        if not isinstance(schema, Mapping):
            issue(target, "invalid_input_schema", "Tool inputSchema must be a JSON Schema object.")
            catalog.append({"name": target, "schema_valid": False})
            continue

        if schema.get("type") not in (None, "object"):
            issue(target, "invalid_schema_root_type", "Tool inputSchema root type must be 'object'.")

        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            issue(target, "invalid_schema_properties", "inputSchema.properties must be an object.")
            properties = {}

        required = schema.get("required", [])
        if not isinstance(required, list) or any(not isinstance(key, str) for key in required):
            issue(target, "invalid_schema_required", "inputSchema.required must be a list of strings.")
            required = []
        else:
            unknown = sorted(set(required) - set(properties))
            if unknown:
                issue(
                    target,
                    "unknown_required_property",
                    "Required properties are not declared in properties: " + ", ".join(unknown),
                )

        try:
            json.dumps(schema, allow_nan=False)
        except (TypeError, ValueError):
            issue(target, "non_json_schema", "inputSchema must be JSON-serializable without NaN or Infinity.")

        catalog.append(
            {
                "name": target,
                "schema_valid": not any(error["target"] == target for error in errors),
                "property_count": len(properties),
                "required_count": len(required),
            }
        )

    return {
        "schema_version": 1,
        "tool_count": len(tools),
        "tools": catalog,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }
