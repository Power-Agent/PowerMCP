"""PowerMCP's powerio conversion server — a thin wrapper over the canonical
``powerio.mcp.server`` that ships with the powerio package.

powerio is a core dependency (see ``powermcp.registry`` / ``pyproject.toml``), so
the standalone server no longer keeps its own copy of the conversion/summary/
matrix tools: it re-exports the canonical FastMCP ``mcp`` instance and every
tool registered on it, and adds the handful of folder/Parquet tools that are not
yet upstream. This keeps the eight text-format tools (``convert_case``,
``save_case``, ``case_summary``, ``parse_case``, ``normalize_case``,
``case_to_json``, ``compute_matrix``, ``dense_view``) in lockstep with powerio
with zero divergence to hand-sync.

The overlay tools below (``read_pypsa_csv_folder`` / ``write_pypsa_csv_folder``
and ``read_gridfm`` / ``write_gridfm``) wrap powerio library functions that the
canonical server does not expose as MCP tools yet. They should migrate into
``powerio.mcp.server`` upstream; once a powerio release includes them, delete
them here and this module becomes a pure re-export.

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
    # Private helpers reused by the overlay tools below so they share the exact
    # input-resolution and summary shape of the canonical tools. Pinned to a
    # powerio version that exports them (see pyproject's powerio requirement).
    _load,
    _summary,
)


@mcp.tool()
def read_pypsa_csv_folder(folder: str) -> dict:
    """Read a PyPSA static CSV folder into the JSON transport plus a summary.

    ``folder`` is a directory of PyPSA component CSVs (``buses.csv``,
    ``generators.csv``, ``lines.csv``, ...). PyPSA CSV is a folder format with
    no single-file text form, so it can't go through ``parse_case`` /
    ``convert_case``; use this to bring such a dataset into the transport, then
    pass the returned ``json`` to any other tool.

    Returns ``{"json": <transport string>, "summary": <case_summary fields>,
    "warnings": [<read fidelity notes>]}``.
    """
    try:
        case = powerio.read_pypsa_csv_folder(folder)
    except powerio.PowerIOError as exc:
        raise ValueError(f"parse failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"cannot read folder: {exc}") from exc
    return {
        "json": case.to_json(),
        "summary": _summary(case),
        "warnings": list(getattr(case, "read_warnings", []) or []),
    }


@mcp.tool()
def write_pypsa_csv_folder(
    out_dir: str,
    path: "str | None" = None,
    content: "str | None" = None,
    json: "str | None" = None,
    format: str = "matpower",
) -> dict:
    """Write a case out as a PyPSA static CSV folder.

    Converts any case — a file ``path``, inline ``content`` (with ``format``),
    or the ``json`` transport from ``parse_case`` — to PyPSA's CSV component
    tables under ``out_dir`` (created if needed). This is the PyPSA-CSV
    counterpart of ``save_case`` for the folder format.

    Returns ``{"dir": <folder written>, "files": [<csv paths>],
    "warnings": [<fidelity notes>]}``.
    """
    case = _load(path, content, json, format)
    try:
        result = case.write_pypsa_csv_folder(out_dir)
    except powerio.PowerIOError as exc:
        raise ValueError(f"conversion failed: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"write failed: {exc}") from exc
    return {
        "dir": result.get("dir", out_dir),
        "files": list(result.get("files", [])),
        "warnings": list(result.get("warnings", [])),
    }


@mcp.tool()
def read_gridfm(dir: str, scenario: int = 0) -> dict:
    """Read one scenario of a gridfm-datakit Parquet dataset into the transport.

    ``dir`` is resolved leniently: the ``raw/`` directory holding the parquet
    files, a ``<case>/`` directory with a ``raw/`` child, or a parent with one
    ``*/raw/`` child all work. ``scenario`` selects one snapshot from a batch
    (``0``, the base case, by default). The read is lossy but recovers
    everything a power flow needs; what it can't recover is in ``warnings``.

    Returns ``{"json": <transport string>, "summary": <case_summary fields>,
    "scenario": <int>, "warnings": [<fidelity notes>]}``. Requires a powerio
    build with the native gridfm reader (published wheels include it).
    """
    try:
        result = powerio.read_gridfm(dir, scenario)
    except powerio.PowerIOError as exc:
        raise ValueError(f"parse failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {exc}") from exc
    except ImportError as exc:
        raise ValueError(str(exc)) from exc
    except OSError as exc:
        raise ValueError(f"cannot read dataset: {exc}") from exc
    case = result.network
    return {
        "json": case.to_json(),
        "summary": _summary(case),
        "scenario": int(result.scenario),
        "warnings": list(result.warnings),
    }


@mcp.tool()
def write_gridfm(
    out_dir: str,
    path: "str | None" = None,
    content: "str | None" = None,
    json: "str | None" = None,
    format: str = "matpower",
    scenario: int = 0,
    include_y_bus: bool = True,
    include_taps: bool = True,
    include_shifts: bool = True,
) -> dict:
    """Write a case as a gridfm-datakit Parquet dataset under ``out_dir``.

    Converts any case — a file ``path``, inline ``content`` (with ``format``),
    or the ``json`` transport — and writes the gridfm layout
    (``<case>/raw/*.parquet`` plus ``gridfm_meta.json``). ``scenario`` tags the
    snapshot id; the ``include_*`` flags toggle the Y-bus, tap, and shift
    columns.

    Returns the writer's report ``{"dir": ..., "files": [...], ...}``. Requires
    a powerio build with the native gridfm writer (published wheels include it).
    """
    case = _load(path, content, json, format)
    try:
        result = case.write_gridfm(
            out_dir,
            scenario,
            include_y_bus=include_y_bus,
            include_taps=include_taps,
            include_shifts=include_shifts,
        )
    except powerio.PowerIOError as exc:
        raise ValueError(f"conversion failed: {exc}") from exc
    except ImportError as exc:
        raise ValueError(str(exc)) from exc
    except OSError as exc:
        raise ValueError(f"write failed: {exc}") from exc
    return dict(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
