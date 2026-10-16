"""Canonical PowerIO tools through the PowerMCP stdio runner.

Every other powerio test calls the tool functions in process, which skips the
SDK's argument handling. The SDK parses a string argument whose text is JSON
before validation, so only a real stdio session proves a ``powerio_ir``
argument reaches the tool intact.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("powerio", minversion="0.11.2")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

CASE9 = Path(__file__).resolve().parent / "data" / "case9.m"

TIMEOUT = 60.0


def _run(steps):
    """Drive one stdio session, returning whatever ``steps`` returns.

    ``steps`` is an async callable taking the initialized session.
    """

    async def go():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "powermcp", "run", "powerio"],
            env=dict(os.environ),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=TIMEOUT) as session:
                await asyncio.wait_for(session.initialize(), TIMEOUT)
                return await steps(session)

    return asyncio.run(go())


def _payload(result):
    assert not result.is_error, result.content[0].text
    return json.loads(result.content[0].text)


def test_launch_serves_the_canonical_tools():
    async def steps(session):
        return sorted(t.name for t in (await session.list_tools()).tools)

    required = {
        "about",
        "calc_matrix",
        "diagnostics",
        "display",
        "emit",
        "parse",
        "summarize",
        "to_balanced",
        "to_balanced_report",
        "to_normalized",
    }
    assert required <= set(_run(steps))


def test_a_path_argument_survives_the_transport():
    async def steps(session):
        return _payload(await session.call_tool("summarize", {"path": str(CASE9)}))

    summary = _run(steps)
    assert summary["elements"]["buses"] == 9


def test_non_json_content_survives_the_transport():
    async def steps(session):
        return _payload(
            await session.call_tool(
                "emit",
                {
                    "format": "psse",
                    "content": CASE9.read_text(),
                    "source_format": "matpower",
                },
            )
        )

    assert _run(steps)["text"]


def test_the_json_transport_round_trips_over_the_transport():
    async def steps(session):
        parsed = _payload(await session.call_tool("parse", {"path": str(CASE9)}))
        assert parsed["value_type"] == "powerio.BalancedNetwork"
        return _payload(
            await session.call_tool(
                "summarize", {"powerio_ir": parsed["powerio_ir"]}
            )
        )

    assert _run(steps)["elements"]["buses"] == 9


def test_ir_diagnostics_and_summary_over_the_transport():
    async def steps(session):
        parsed = _payload(
            await session.call_tool(
                "parse", {"path": str(CASE9)}
            )
        )
        package = parsed["powerio_ir"]
        assert not (
            await session.call_tool("diagnostics", {"powerio_ir": package})
        ).is_error
        return _payload(
            await session.call_tool("summarize", {"powerio_ir": package})
        )

    assert _run(steps)["elements"]["buses"] == 9
