"""``translate_to_plexos`` -- translate a Sienna PSY-JSON system to PLEXOS via r2x.

Calls r2x directly (``r2x_core``, ``r2x_sienna_to_plexos``, ``r2x_plexos``) --
there is no PowerMCP-authored bridge/interop module, matching PLEXOSDB's
(issue #53) ``translate_to_sienna`` which does the reverse translation the same
way. Verified against r2x 2.1.0 (2026-08-07): ``r2x_sienna_to_plexos.sienna_to_plexos``
is a plain function, ``System -> System``, that maps Sienna component types
(``r2x_sienna.models``) onto PLEXOS component types (``r2x_plexos.models``,
e.g. ``PLEXOSNode``, ``PLEXOSGenerator``); this always succeeds when the
sienna_to_plexos rules cover every component type present. A full PLEXOS
XML/database export additionally requires ``r2x_plexos.PLEXOSExporter``, which
needs more PLEXOS-specific configuration (at minimum ``horizon_year``) that
this tool does not have a way to infer from a bare Sienna system -- see the
``export_xml`` docstring below and SIENNA/README.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .system_tools import R2X_NOT_INSTALLED_MESSAGE, _component_counts


def translate_to_plexos(
    psy_json_path: str,
    output_path: str | None = None,
    export_xml: bool = False,
    horizon_year: int | None = None,
    model_name: str = "default",
    prime_mover_mapping: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Translate a Sienna PSY-JSON system to PLEXOS-shaped components via r2x.

    Always performs the System-level translation (``r2x_sienna_to_plexos.sienna_to_plexos``)
    and returns component counts for the result. If ``output_path`` is given, the
    translated system is additionally written out as JSON at that path.

    If ``export_xml=True``, this also attempts a full PLEXOS XML/database export via
    ``r2x_plexos.PLEXOSExporter`` into the directory given by ``output_path``. This is
    best-effort: PLEXOS export needs more configuration than a bare Sienna system
    carries (at minimum ``horizon_year``; PLEXOSExporter may also need a template).
    Failures are reported in the ``xml_export`` field rather than raised, so the
    System-level translation result is still returned.
    """
    try:
        from r2x_core import PluginContext, System
        from r2x_plexos import PLEXOSConfig, PLEXOSExporter
        from r2x_sienna_to_plexos import SiennaToPlexosConfig, sienna_to_plexos
    except ImportError:
        return {
            "ok": False,
            "error_type": "r2x_not_installed",
            "message": R2X_NOT_INSTALLED_MESSAGE,
        }

    path = Path(psy_json_path).expanduser()
    if not path.is_file():
        return {
            "ok": False,
            "error_type": "file_not_found",
            "message": f"PSY JSON file not found: {path}",
            "path": str(path),
        }

    try:
        source_system = System.from_json(path)
    except Exception as exc:
        return {
            "ok": False,
            "error_type": "load_failed",
            "message": f"Failed to load source system from {path}: {exc}",
            "path": str(path),
        }

    try:
        config = SiennaToPlexosConfig(prime_mover_mapping=prime_mover_mapping or {})
        translated = sienna_to_plexos(source_system, config)
    except Exception as exc:
        return {
            "ok": False,
            "error_type": "translate_failed",
            "message": f"r2x sienna_to_plexos translation failed: {exc}",
            "path": str(path),
        }

    component_counts = _component_counts(translated)
    result: dict[str, Any] = {
        "ok": True,
        "source_path": str(path),
        "translated_component_counts": component_counts,
        "translated_total_components": sum(component_counts.values()),
    }

    out = Path(output_path).expanduser() if output_path else None
    if out is not None:
        try:
            translated.to_json(out)
            result["output_json_path"] = str(out)
        except Exception as exc:
            result["output_json_error"] = str(exc)

    if export_xml:
        if out is None:
            result["xml_export"] = {
                "ok": False,
                "message": "export_xml=True requires output_path (used as the PLEXOS export directory).",
            }
        else:
            export_dir = out.parent if out.suffix else out
            try:
                plexos_cfg = PLEXOSConfig(
                    output_path=str(export_dir),
                    model_name=model_name,
                    horizon_year=horizon_year,
                )
                ctx = PluginContext(config=plexos_cfg, system=translated)
                PLEXOSExporter.from_context(ctx).run()
                result["xml_export"] = {"ok": True, "output_path": str(export_dir)}
            except Exception as exc:
                result["xml_export"] = {"ok": False, "message": str(exc)}

    return result


def register_translate_tools(mcp: FastMCP) -> None:
    """Register PLEXOS-translation tools with the MCP server."""
    mcp.tool(
        name="translate_to_plexos",
        description=(
            "Translate a Sienna PSY-JSON system to PLEXOS-shaped components using r2x's "
            "sienna_to_plexos translation rules. Always returns component counts for the "
            "translated system; pass output_path to also write it as JSON. Pass "
            "export_xml=True to additionally attempt a full PLEXOS XML/database export "
            "(best-effort; requires horizon_year and reports failure in xml_export rather "
            "than raising)."
        ),
    )(translate_to_plexos)
