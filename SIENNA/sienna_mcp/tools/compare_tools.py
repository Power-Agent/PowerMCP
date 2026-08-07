"""``compare_solutions`` -- diff a Sienna-side artifact against a PLEXOS-side one.

Calls r2x directly (``r2x_core.System.from_json``) -- no PowerMCP-authored
bridge/interop module. Each input path may be either:

* an R2X/infrasys **System JSON** -- a native Sienna PSY export, a
  ``translate_to_plexos`` output from this connector, or a
  ``translate_to_sienna`` export from the sibling PLEXOSDB connector (issue
  #53) -- compared by component-type counts, or
* a plain **results JSON** (e.g. written by this connector's
  ``run_sienna_solve``, or exported by any external tool from a PLEXOS
  solution) -- compared by shared numeric top-level fields (objective value,
  total cost, etc.).

r2x does not ship a PLEXOS *solution* (as opposed to input database) reader as
of r2x 2.1.0 / plexosdb 1.5.0 -- ``plexosdb`` (an r2x transitive dependency)
exposes PLEXOS input-database CRUD, the same surface PLEXOSDB (#53) wraps, not
solved-results parsing. So the PLEXOS side of a *results* comparison is
necessarily a results JSON produced some other way (manually, or by a
downstream tool), not a call this connector makes into r2x. This is a known,
documented gap -- see SIENNA/README.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .system_tools import R2X_NOT_INSTALLED_MESSAGE, _component_counts


def _load_side(path_str: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Load one side of the comparison. Returns (loaded, error)."""
    from r2x_core import System

    path = Path(path_str).expanduser()
    if not path.is_file():
        return None, {
            "error_type": "file_not_found",
            "message": f"File not found: {path}",
            "path": str(path),
        }

    try:
        system = System.from_json(path)
        return {
            "kind": "system",
            "path": str(path),
            "component_counts": _component_counts(system),
        }, None
    except Exception:
        pass  # not a System JSON -- fall through to plain results JSON

    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("top-level JSON must be an object")
        return {"kind": "results", "path": str(path), "data": data}, None
    except Exception as exc:
        return None, {
            "error_type": "unreadable",
            "message": f"Could not parse {path} as an R2X system or a results JSON object: {exc}",
            "path": str(path),
        }


def compare_solutions(
    sienna_path: str,
    plexos_path: str,
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Compare a Sienna-side artifact against a PLEXOS-side artifact.

    ``sienna_path``/``plexos_path`` are each either an R2X System JSON (compared
    by component-type counts) or a results JSON (compared by shared numeric
    top-level fields; restrict to specific fields with ``metrics``). Comparing a
    System against a results file returns both sides verbatim with a note that
    nothing numeric was computed -- pass like-for-like (system vs system, or
    results vs results).
    """
    try:
        import r2x_core  # noqa: F401  -- import-time availability check only
    except ImportError:
        return {
            "ok": False,
            "error_type": "r2x_not_installed",
            "message": R2X_NOT_INSTALLED_MESSAGE,
        }

    sienna_loaded, err = _load_side(sienna_path)
    if err is not None:
        return {"ok": False, "side": "sienna", **err}

    plexos_loaded, err = _load_side(plexos_path)
    if err is not None:
        return {"ok": False, "side": "plexos", **err}

    assert sienna_loaded is not None and plexos_loaded is not None
    result: dict[str, Any] = {"ok": True, "sienna": sienna_loaded, "plexos": plexos_loaded}

    if sienna_loaded["kind"] == "system" and plexos_loaded["kind"] == "system":
        sc = sienna_loaded["component_counts"]
        pc = plexos_loaded["component_counts"]
        keys = sorted(set(sc) | set(pc))
        result["component_count_diff"] = {
            k: {"sienna": sc.get(k, 0), "plexos": pc.get(k, 0), "diff": sc.get(k, 0) - pc.get(k, 0)}
            for k in keys
        }
    elif sienna_loaded["kind"] == "results" and plexos_loaded["kind"] == "results":
        sd, pd = sienna_loaded["data"], plexos_loaded["data"]
        candidate_keys = metrics if metrics is not None else sorted(set(sd) & set(pd))
        diffs: dict[str, Any] = {}
        for k in candidate_keys:
            sv, pv = sd.get(k), pd.get(k)
            if isinstance(sv, (int, float)) and isinstance(pv, (int, float)) and not isinstance(sv, bool) and not isinstance(pv, bool):
                diffs[k] = {
                    "sienna": sv,
                    "plexos": pv,
                    "diff": sv - pv,
                    "pct_diff": ((sv - pv) / pv * 100.0) if pv else None,
                }
        result["metric_diff"] = diffs
        if metrics is None and not diffs:
            result["note"] = "No shared numeric top-level fields found; pass metrics=[...] explicitly."
    else:
        result["note"] = (
            "One side is a System JSON and the other is a results JSON; nothing directly "
            "comparable was computed. Compare like-for-like (system vs system, or results vs results)."
        )

    return result


def register_compare_tools(mcp: FastMCP) -> None:
    """Register comparison tools with the MCP server."""
    mcp.tool(
        name="compare_solutions",
        description=(
            "Compare a Sienna-side artifact against a PLEXOS-side artifact. Each of "
            "sienna_path/plexos_path is either an R2X System JSON (compared by "
            "component-type counts via r2x_core.System.from_json) or a plain results JSON "
            "such as run_sienna_solve's output (compared by shared numeric fields, "
            "optionally restricted with metrics=[...])."
        ),
    )(compare_solutions)
