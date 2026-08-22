"""PowerMCP's PLEXOSDB connector: a thin re-export of the upstream ``plexosdb-mcp``
server plus two additional tools, ``translate_to_sienna`` and ``compare_solutions``,
that call the ``r2x`` translation framework directly.

plexosdb-mcp (https://github.com/NatLabRockies/plexosdb/tree/main/src/plexosdb-mcp)
is a purpose-built MCP server for PLEXOS database CRUD: session lifecycle, object/
membership/property discovery and editing, and XML/CSV export -- 29 tools in total.
It needs no PLEXOS license, install, or vendor network call: it reads and writes the
PLEXOS XML database format directly via the open-source ``plexosdb`` library. See
PLEXOSDB/README.md for the (currently git-only) install step.

This module keeps no copy of plexosdb-mcp's tool implementations -- it builds the
upstream FastMCP server object as-is (``build_mcp_server``) and re-exports it, the
same shape as ``powerio/powerio_mcp.py``'s ``mcp = _server.mcp``. plexosdb-mcp builds
its server via a factory rather than a module-level singleton, so calling that
factory once at import time is the direct analogue here.

The two tools added below call r2x's real, public API directly: ``r2x_plexos.
PLEXOSParser`` builds an r2x System from a PLEXOS XML study, ``r2x_plexos_to_sienna.
plexos_to_sienna`` translates it, and ``r2x_sienna.SiennaExporter`` writes Sienna PSY
JSON. There is no PowerMCP-authored bridge/interop module in between -- mirroring how
pandapower/PyPSA/Egret/ANDES each import powerio directly rather than through a
wrapper.

Run over stdio with ``python PLEXOSDB/plexosdb_mcp/main.py`` (or
``powermcp run plexosdb``). Deliberately launched as a *script*, not
``python -m plexosdb_mcp.main``: this package is named ``plexosdb_mcp`` to
mirror the upstream ``plexosdb-mcp`` distribution it re-exports, so running it
in module form from the repo root would put ``PLEXOSDB/`` on ``sys.path`` and
make the bare ``import plexosdb_mcp`` below resolve to *this* package instead
of the real, installed one -- a self-shadow. Script launch only puts this
file's own directory on ``sys.path``, so the import correctly falls through to
site-packages. See ``powermcp/registry.py``'s ``plexosdb`` entry.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Path containment for model-supplied tool arguments, same policy as every
# other bundled server. Bootstrap the repo root only long enough to import
# powermcp when running from a raw clone (installed wheels find it on
# site-packages).
_repo_root = str(Path(__file__).resolve().parents[2])
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import PathNotAllowed, checked_path
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

from plexosdb_mcp import server as _server

# -- thin re-export of plexosdb-mcp's own server -------------------------- #
MCPServerState = _server.MCPServerState
build_mcp_server = _server.build_mcp_server
# NOTE: this is upstream's own CLI helper (--version/doctor/capabilities
# subcommands, or a bare stdio run with no extra tools if invoked with none).
# Re-exported for parity/diagnostics only; it is NOT how this module serves
# translate_to_sienna/compare_solutions -- calling it with no subcommand builds
# a *fresh* upstream-only server via its own build_mcp_server() call, missing
# the two tools added below. The actual entry point that serves the extended
# `mcp` object (all upstream tools + ours) is `mcp.run(...)` under
# `if __name__ == "__main__"` at the bottom of this file.
main = _server.main

mcp = build_mcp_server()

__all__ = [
    "mcp",
    "MCPServerState",
    "build_mcp_server",
    "main",
    "translate_to_sienna",
    "compare_solutions",
]


@mcp.tool()
def translate_to_sienna(
    xml_path: str,
    model_name: str,
    output_path: str,
    horizon_year: int | None = None,
    system_base_power: float = 100.0,
    scenario: str = "base",
) -> dict[str, Any]:
    """Translate a PLEXOS XML study to Sienna PSY JSON via r2x.

    Calls r2x's own plugin pipeline directly, with no PowerMCP-authored bridge
    code in between:

    1. ``r2x_plexos.PLEXOSParser`` parses ``xml_path``/``model_name`` into an
       ``r2x_core.System``.
    2. ``r2x_plexos_to_sienna.plexos_to_sienna`` translates that System to a
       Sienna-shaped System.
    3. ``r2x_sienna.SiennaExporter`` writes it to ``output_path`` as Sienna PSY
       JSON -- the format the sibling SIENNA connector (PowerMCP issue #54)
       loads and solves.

    Parameters
    ----------
    xml_path:
        Path to the PLEXOS XML study (a run directory or a single .xml file).
    model_name:
        Name of the PLEXOS ``Model`` object to translate. Use plexosdb-mcp's
        own ``list_models`` tool against the same file to discover valid names.
    output_path:
        Destination path for the Sienna PSY JSON file.
    horizon_year:
        Optional horizon year passed through to the PLEXOS parser.
    system_base_power:
        System base power in MVA for per-unit calculations (default 100.0).
    scenario:
        Scenario identifier recorded in the exported system (default "base").

    Returns
    -------
    dict with ``ok``, ``output_path``, and a ``component_types`` count summary
    of the translated Sienna system.

    Notes
    -----
    r2x_plexos 0.2.0 has a bug resolving a PLEXOS model's simulation horizon:
    it reads the Horizon object's "Chrono Date From"/"Chrono Date To"
    attributes and only catches ``AssertionError`` if they are unset, but
    plexosdb instead raises ``plexosdb.exceptions.NotFoundError`` when the
    attribute isn't registered for the class at all (not a subclass of
    ``AssertionError``) -- the common case for studies that don't use
    PLEXOS's chronological/rolling horizon feature. This is already fixed in
    r2x_plexos>=0.3.0 (confirmed against the released wheel), which is what
    this package now pins. Getting that version installed cleanly still
    requires ``--prerelease=allow`` today, because r2x_plexos>=0.3.0 needs
    plexosdb>=1.6.0, whose own ``plexos2duckdb>=0.1.0b11`` dependency has no
    non-yanked stable release yet (epri-dev/plexos2duckdb#3). See
    PLEXOSDB/README.md for the install command and both upstream issues
    (NatLabRockies/R2X#299, epri-dev/plexos2duckdb#3).
    """
    try:
        xml_path = checked_path(xml_path, purpose="xml_path")
        output_path = checked_path(output_path, purpose="output_path", for_write=True)
    except PathNotAllowed as exc:
        return {"ok": False, "error": str(exc)}

    from r2x_core import PluginContext
    from r2x_plexos import PLEXOSConfig, PLEXOSParser
    from r2x_plexos_to_sienna import PlexosToSiennaConfig, plexos_to_sienna
    from r2x_sienna import SiennaExporter, SiennaExporterConfig

    plexos_config = PLEXOSConfig(fpath=xml_path, model_name=model_name, horizon_year=horizon_year)
    parse_ctx = PluginContext(config=plexos_config)
    parse_ctx = PLEXOSParser.from_context(parse_ctx).run()

    sienna_system = plexos_to_sienna(parse_ctx.system, PlexosToSiennaConfig())

    export_config = SiennaExporterConfig(
        output_path=output_path,
        system_base_power=system_base_power,
        scenario=scenario,
    )
    export_ctx = PluginContext(config=export_config, system=sienna_system)
    SiennaExporter.from_context(export_ctx).run()

    component_types = {
        component_type.__name__: len(list(sienna_system.get_components(component_type)))
        for component_type in sienna_system.get_component_types()
    }
    return {
        "ok": True,
        "output_path": output_path,
        "model_name": model_name,
        "component_types": component_types,
    }


@mcp.tool()
def compare_solutions(
    xml_path_a: str,
    model_name_a: str,
    xml_path_b: str,
    model_name_b: str,
) -> dict[str, Any]:
    """Structurally compare two PLEXOS models via r2x's parsed System representation.

    Parses both models with ``r2x_plexos.PLEXOSParser`` -- the same real r2x API
    ``translate_to_sienna`` uses -- and diffs their component-type counts.
    Useful for comparing two scenarios of the same study, or a study before and
    after an edit made through plexosdb-mcp's own CRUD tools, without a PLEXOS
    license or solve step (solving is the paired SIENNA connector's job,
    PowerMCP issue #54; this connector never solves anything).

    Parameters
    ----------
    xml_path_a, model_name_a:
        The first PLEXOS study/model to parse.
    xml_path_b, model_name_b:
        The second PLEXOS study/model to parse.

    Returns
    -------
    dict with per-component-type counts for each side and the set of
    component types whose count differs between them.

    Notes
    -----
    Uses the same ``r2x_plexos>=0.3.0`` pin documented on ``translate_to_sienna``,
    which fixes the upstream Horizon-resolution bug this connector previously hit.
    """
    try:
        xml_path_a = checked_path(xml_path_a, purpose="xml_path_a")
        xml_path_b = checked_path(xml_path_b, purpose="xml_path_b")
    except PathNotAllowed as exc:
        return {"ok": False, "error": str(exc)}

    from r2x_core import PluginContext
    from r2x_plexos import PLEXOSConfig, PLEXOSParser

    def _component_counts(xml_path: str, model_name: str) -> dict[str, int]:
        config = PLEXOSConfig(fpath=xml_path, model_name=model_name)
        ctx = PluginContext(config=config)
        ctx = PLEXOSParser.from_context(ctx).run()
        return {
            component_type.__name__: len(list(ctx.system.get_components(component_type)))
            for component_type in ctx.system.get_component_types()
        }

    counts_a = _component_counts(xml_path_a, model_name_a)
    counts_b = _component_counts(xml_path_b, model_name_b)

    all_types = sorted(set(counts_a) | set(counts_b))
    differences = {
        t: {"a": counts_a.get(t, 0), "b": counts_b.get(t, 0)}
        for t in all_types
        if counts_a.get(t, 0) != counts_b.get(t, 0)
    }

    return {
        "ok": True,
        "model_a": {"xml_path": xml_path_a, "model_name": model_name_a, "component_types": counts_a},
        "model_b": {"xml_path": xml_path_b, "model_name": model_name_b, "component_types": counts_b},
        "differences": differences,
        "identical": not differences,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
