"""PowerMCP's powerio conversion server — a thin wrapper over the canonical
``powerio.mcp.server`` that ships with the powerio package.

powerio is a core dependency (see ``powermcp.registry`` / ``pyproject.toml``), so
the standalone server keeps no copy of the conversion/summary/matrix tools: it
re-exports the canonical FastMCP ``mcp`` instance and every tool registered on
it. As of powerio 0.2.2 that is twelve tools — the eight text-format tools
(``convert_case``, ``save_case``, ``case_summary``, ``parse_case``,
``normalize_case``, ``case_to_json``, ``compute_matrix``, ``dense_view``) plus
the four folder/Parquet tools (``read_pypsa_csv_folder`` /
``write_pypsa_csv_folder`` and ``read_gridfm`` / ``write_gridfm``) that moved
upstream in powerio #119. They stay in lockstep with powerio, nothing to
hand-sync.

The one overlay below, ``read_display_file``, wraps powerio's ``.pwd`` display
API (``parse_display_file``, added in powerio #120) that the canonical server
does not expose as an MCP tool yet. It should migrate into ``powerio.mcp.server``
upstream; once a powerio release includes it, delete it here and this module
becomes a pure re-export.

Run over stdio with ``python powerio_mcp.py`` (or ``powermcp run powerio``).
"""

from __future__ import annotations

import powerio

# Re-export the canonical server and its tools verbatim. Importing
# ``powerio.mcp.server`` also fails loudly if the repo's own ``powerio/``
# directory shadows the installed package (it has no ``mcp`` submodule), so no
# separate shadow guard is needed.
from powerio.mcp.server import (  # noqa: F401  (re-exported for `powermcp run` and tests)
    mcp,
    convert_case,
    save_case,
    case_summary,
    parse_case,
    normalize_case,
    case_to_json,
    compute_matrix,
    dense_view,
    read_pypsa_csv_folder,
    write_pypsa_csv_folder,
    read_gridfm,
    write_gridfm,
)


@mcp.tool()
def read_display_file(path: str) -> dict:
    """Decode a PowerWorld ``.pwd`` display file into canvas + substation layout.

    A ``.pwd`` is the one-line *display* artifact (diagram geometry), separate
    from the network case in a ``.pwb`` / ``.aux``. This reads the diagram's
    canvas size, its stamp, and each substation's display coordinates, so a
    client can place buses on a one-line or map without PowerWorld installed.

    Returns ``{"kind": "powerworld", "canvas_width": <int>,
    "canvas_height": <int>, "stamp": <int>, "substations":
    [{"number": <int>, "name": <str>, "x": <float>, "y": <float>}, ...]}``.
    """
    try:
        display = powerio.parse_display_file(path)
    except powerio.PowerIOError as exc:
        raise ValueError(f"parse failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"cannot read file: {exc}") from exc
    # powerio's DisplayData is generic (kind + data); only "powerworld" yields a
    # PwdDisplay. Reject any other kind with a clean error instead of an opaque
    # AttributeError if a future powerio adds one (the pin is a >=0.2.2 floor).
    if display.kind != "powerworld":
        raise ValueError(f"unsupported display format: {display.kind!r}")
    pwd = display.data
    return {
        "kind": display.kind,
        "canvas_width": pwd.canvas_width,
        "canvas_height": pwd.canvas_height,
        "stamp": pwd.stamp,
        "substations": [
            {"number": s.number, "name": s.name, "x": s.x, "y": s.y}
            for s in pwd.substations
        ],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
