from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .core import hope_case_info, hope_output_summary, hope_run_hope

mcp = FastMCP(
    "hope-mcp",
    instructions=(
        "HOPE proof-of-concept MCP server for the local Julia repository. "
        "Use the whitelisted case id md_gtep_clean."
    ),
)


@mcp.tool(
    name="hope_case_info",
    description="Return metadata and output inventory for the whitelisted HOPE case.",
)
def hope_case_info_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    return hope_case_info(case_id)


@mcp.tool(
    name="hope_output_summary",
    description="Summarize existing HOPE output CSVs for the whitelisted case without running Julia.",
)
def hope_output_summary_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    return hope_output_summary(case_id)


@mcp.tool(
    name="hope_run_hope",
    description="Run HOPE synchronously for the whitelisted case and return a compact summary.",
)
def hope_run_hope_tool(case_id: str = "md_gtep_clean") -> dict[str, Any]:
    return hope_run_hope(case_id)


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
