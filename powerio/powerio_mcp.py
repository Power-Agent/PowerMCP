"""A FastMCP server exposing powerio: case conversion, summaries, the JSON
transport, and sparse matrix views.

Tools for LLM agents, accepting a filesystem ``path``, inline ``content``, or
(for ``save_case``, ``compute_matrix``, and ``dense_view``) the JSON transport
string:

- ``convert_case``: convert a case between formats, returning the text and any
  fidelity warnings.
- ``save_case``: convert and write the result to a file on disk, staging input
  for path-only consumers.
- ``case_summary``: counts, base MVA, source format, and connectivity, with no
  scipy/numpy in the loop.
- ``parse_case`` / ``normalize_case`` / ``case_to_json``: emit the JSON
  transport (``Network.to_json``), the cheap handoff between tool calls.
- ``compute_matrix``: the sparse matrix views in COO form as plain lists.
- ``dense_view``: the dense table view as plain lists and dicts.

Run over stdio with the ``powerio-mcp`` console script (or ``python -m
powerio.mcp``). The server is a thin wrapper over the powerio Python API; it
never reimplements parsing or math, and inline content converts in memory with
no temp file staging.

This file is the standalone copy of the canonical ``powerio.mcp.server``
(``python/powerio/mcp/server.py`` in eigenergy/powerio); land changes there
first and sync them here. Requires powerio >= 0.1.0 (convert_str).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import powerio
from mcp.server.fastmcp import FastMCP

# Fail fast if `import powerio` resolved to something without the real API — e.g.
# this server's own powerio/ directory shadowing the package as a PEP 420
# namespace (editable installs / PYTHONPATH / pytest rootdir).
if not hasattr(powerio, "parse_file"):  # pragma: no cover
    raise ImportError(
        "the 'powerio' package is not importable (the repo's powerio/ directory "
        "may be shadowing it); install it: pip install 'powerio[mcp,matrix]'"
    )

mcp = FastMCP("PowerIO Conversion Server")

_MATRIX_KINDS = (
    "bprime", "bdoubleprime", "ybus_real", "ybus_imag",
    "adjacency", "ptdf", "lodf", "laplacian", "lacpf",
)


def _one_input(path: Optional[str], content: Optional[str]) -> None:
    if (path is None) == (content is None):
        raise ValueError("provide exactly one of `path` or `content`")


def _parse(path: Optional[str], content: Optional[str], format: str) -> "powerio.Network":
    """Parse from exactly one of ``path`` or inline ``content``, mapping powerio
    and filesystem errors to ValueError so MCP clients see one error shape."""
    _one_input(path, content)
    try:
        if path is not None:
            return powerio.parse_file(path)
        return powerio.parse_str(content, format)
    except powerio.PowerIOError as exc:
        raise ValueError(f"parse failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {exc}") from exc


def _load(
    path: Optional[str], content: Optional[str], json: Optional[str], format: str
) -> "powerio.Network":
    """Like ``_parse`` but also accepts the JSON transport string."""
    if sum(v is not None for v in (path, content, json)) != 1:
        raise ValueError("provide exactly one of `path`, `content`, or `json`")
    if json is None:
        return _parse(path, content, format)
    try:
        return powerio.from_json(json)
    except powerio.PowerIOError as exc:
        raise ValueError(f"parse failed: {exc}") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"parse failed: {exc}") from exc


def _summary(case: "powerio.Network") -> Dict[str, Any]:
    return {
        "name": case.name,
        "base_mva": case.base_mva,
        "source_format": case.source_format,
        "n_buses": case.n_buses,
        "n_branches": case.n_branches,
        "n_gens": case.n_gens,
        "n_loads": case.n_loads,
        "n_shunts": case.n_shunts,
        "is_radial": case.is_radial,
        "n_connected_components": case.n_connected_components,
        "connectivity_report": case.connectivity_report(),
    }


@mcp.tool()
def convert_case(
    to: str,
    path: Optional[str] = None,
    content: Optional[str] = None,
    from_: Optional[str] = None,
) -> dict:
    """Convert a power system case file to another format, losslessly where the
    target allows.

    Provide exactly one of ``path`` (a file on disk) or ``content`` (inline file
    text). ``to``/``from_`` are format names or aliases: ``matpower`` (``m``),
    ``powermodels-json`` (``pm``), ``egret-json`` (``egret``), ``psse``
    (``raw``), ``powerworld`` (``aux``). The input format is inferred from the
    file extension for ``path``; ``from_`` is REQUIRED with inline ``content``.

    Returns ``{"text": <converted file>, "warnings": [<fidelity notes: data the
    target can't represent, defaults synthesized, or blocks mapped to the nearest
    supported target representation>]}`` (empty for a faithful conversion).
    """
    _one_input(path, content)
    if content is not None and not from_:
        raise ValueError("`from_` is required when converting inline `content`")
    try:
        if path is not None:
            conv = powerio.convert_file(path, to, from_)
        else:
            conv = powerio.convert_str(content, to, from_)
    except powerio.PowerIOError as exc:
        raise ValueError(f"conversion failed: {exc}") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"conversion failed: {exc}") from exc
    return {"text": conv.text, "warnings": list(conv.warnings)}


@mcp.tool()
def save_case(
    to: str,
    out_path: str,
    path: Optional[str] = None,
    content: Optional[str] = None,
    json: Optional[str] = None,
    format: str = "matpower",
    overwrite: bool = False,
) -> dict:
    """Convert a case and write the result to a file on disk.

    Use this to stage input for consumers that only accept file paths: convert
    any case (or the JSON transport from ``parse_case``) to the target format
    and point the other program at ``out_path``. Pick an ``out_path`` extension
    matching ``to`` (``.m``, ``.json``, ``.raw``, ``.aux``).

    ``to`` is a format name or alias: ``matpower`` (``m``), ``powermodels-json``
    (``pm``), ``egret-json`` (``egret``), ``psse`` (``raw``), ``powerworld``
    (``aux``). Provide exactly one of ``path``, ``content`` (with ``format``),
    or ``json`` (the transport string). An existing ``out_path`` is not
    overwritten unless ``overwrite`` is true.

    Returns ``{"path": <absolute path written>, "bytes_written": <count>,
    "warnings": [<fidelity notes>]}``.
    """
    case = _load(path, content, json, format)
    try:
        conv = case.to_format(to)
    except powerio.PowerIOError as exc:
        raise ValueError(f"conversion failed: {exc}") from exc
    try:
        # newline="" disables newline translation so the file is byte-identical
        # to the converter output (and to the CLI) on every platform, and
        # bytes_written below is exact on Windows.
        mode = "w" if overwrite else "x"
        with open(out_path, mode, encoding="utf-8", newline="") as fh:
            fh.write(conv.text)
    except FileExistsError:
        raise ValueError(
            f"refusing to overwrite existing file: {out_path}; pass overwrite=true"
        ) from None
    except OSError as exc:
        raise ValueError(f"write failed: {exc}") from exc
    return {
        "path": os.path.abspath(out_path),
        "bytes_written": len(conv.text.encode("utf-8")),
        "warnings": list(conv.warnings),
    }


@mcp.tool()
def case_summary(
    path: Optional[str] = None,
    content: Optional[str] = None,
    format: str = "matpower",
) -> dict:
    """Summarize a power system case: name, base MVA, source format, element
    counts, and connectivity.

    Provide exactly one of ``path`` or ``content``. For inline ``content``,
    ``format`` names the input format (default ``matpower``). Pulls in no
    scipy/numpy.
    """
    return _summary(_parse(path, content, format))


@mcp.tool()
def parse_case(
    path: Optional[str] = None,
    content: Optional[str] = None,
    format: str = "matpower",
) -> dict:
    """Parse a power system case once and return its JSON transport plus a
    summary.

    Provide exactly one of ``path`` or ``content``. For inline ``content``,
    ``format`` names the input format (default ``matpower``); formats:
    ``matpower``, ``powermodels-json``, ``egret-json``, ``psse``,
    ``powerworld``.

    The returned ``json`` string is the exchange format between tool calls:
    pass it to ``compute_matrix``, ``dense_view``, and ``save_case`` here, or
    to any downstream tool that ingests the transport (e.g. PowerMCP's
    pandapower, egret, and PyPSA bridges), instead of parsing the file again
    on every call.

    Returns ``{"json": <transport string>, "summary": <case_summary fields>}``.
    """
    case = _parse(path, content, format)
    return {"json": case.to_json(), "summary": _summary(case)}


@mcp.tool()
def normalize_case(
    path: Optional[str] = None,
    content: Optional[str] = None,
    format: str = "matpower",
) -> dict:
    """Parse a case and return the JSON transport of its normalized form: per
    unit, radians, out of service elements filtered, buses densely reindexed
    (1-based), bus types canonicalized.

    Use this instead of ``parse_case`` when downstream math wants a computation
    ready case rather than the verbatim source tables. Provide exactly one of
    ``path`` or ``content`` (with ``format``).

    Returns ``{"json": <transport string>, "summary": <fields of the normalized
    case>}``; the ``json`` is accepted everywhere the ``parse_case`` transport
    is.
    """
    case = _parse(path, content, format)
    try:
        norm = case.to_normalized()
    except powerio.PowerIOError as exc:
        raise ValueError(f"normalization failed: {exc}") from exc
    return {"json": norm.to_json(), "summary": _summary(norm)}


@mcp.tool()
def case_to_json(
    path: Optional[str] = None,
    content: Optional[str] = None,
    format: str = "matpower",
) -> dict:
    """Convert a case file (or inline text) to the powerio JSON transport
    string.

    Provide exactly one of ``path`` or ``content`` (with ``format``). The
    returned ``json`` is accepted by ``compute_matrix``, ``dense_view``,
    ``save_case``, and any downstream tool that ingests the transport. Use
    ``parse_case`` instead if you also want the summary.

    Returns ``{"json": <transport string>}``.
    """
    return {"json": _parse(path, content, format).to_json()}


@mcp.tool()
def compute_matrix(
    kind: str,
    path: Optional[str] = None,
    content: Optional[str] = None,
    json: Optional[str] = None,
    format: str = "matpower",
    scheme: str = "bx",
    convention: str = "paper",
) -> dict:
    """Build a sparse matrix view of a case and return it in COO form.

    ``kind`` is one of: ``bprime`` (FDPF B', shuntless), ``bdoubleprime`` (FDPF
    B'' with shunts and taps), ``ybus_real`` / ``ybus_imag`` (Re/Im of Y_bus),
    ``adjacency`` (0/1 bus adjacency), ``ptdf`` (DC PTDF, m×n), ``lodf`` (DC
    LODF, m×m), ``laplacian`` (weighted Laplacian L = A diag(b) Aᵀ), ``lacpf``
    (linearized AC 2n×2n block [[G, -B], [-B, -G]], taps and shifts included).
    ``scheme`` ("bx"|"xb") applies to bprime/bdoubleprime; ``convention``
    ("paper"|"matpower") to ptdf/lodf/laplacian.

    Provide exactly one of ``path``, ``content`` (with ``format``), or
    ``json``, the transport string from ``parse_case`` / ``normalize_case`` /
    ``case_to_json``; passing it skips parsing again.

    Returns ``{"format": "coo", "shape": [rows, cols], "nnz": <count>,
    "data": [...], "row": [...], "col": [...]}`` with plain Python lists.
    Requires scipy (``pip install 'powerio[matrix]'``).
    """
    if kind not in _MATRIX_KINDS:
        raise ValueError(
            f"unknown matrix kind {kind!r}; expected one of: {', '.join(_MATRIX_KINDS)}"
        )
    case = _load(path, content, json, format)
    try:
        if kind == "bprime":
            m = case.bprime(scheme)
        elif kind == "bdoubleprime":
            m = case.bdoubleprime(scheme)
        elif kind in ("ybus_real", "ybus_imag"):
            parts = case.ybus_parts()
            m = parts.g if kind == "ybus_real" else parts.b
        elif kind == "adjacency":
            m = case.adjacency()
        elif kind == "ptdf":
            m = case.ptdf(convention)
        elif kind == "lodf":
            m = case.lodf(convention)
        elif kind == "lacpf":
            m = case.lacpf()
        elif kind == "laplacian":
            m = case.weighted_laplacian(convention)
        else:  # pragma: no cover - unreachable; guarded by the _MATRIX_KINDS check
            raise ValueError(f"unhandled matrix kind {kind!r}")
    except ImportError as exc:
        raise ValueError(str(exc)) from exc
    except powerio.PowerIOError as exc:
        raise ValueError(f"matrix build failed: {exc}") from exc
    coo = m.tocoo()
    return {
        "format": "coo",
        "shape": [int(coo.shape[0]), int(coo.shape[1])],
        "nnz": int(coo.nnz),
        "data": coo.data.tolist(),
        "row": coo.row.tolist(),
        "col": coo.col.tolist(),
    }


@mcp.tool()
def dense_view(
    path: Optional[str] = None,
    content: Optional[str] = None,
    json: Optional[str] = None,
    format: str = "matpower",
) -> dict:
    """Dense table view of a case as plain lists and dicts: counts, base MVA,
    bus ids, branch arrays (from_id, to_id, r, x, b, tap, shift, in_service),
    generator arrays (bus, pg, pmax, pmin, in_service), nodal demand and shunt
    arrays, the reference bus index, connected component count, and radial
    flag.

    Provide exactly one of ``path``, ``content`` (with ``format``), or ``json``
    (the transport string from ``parse_case`` / ``normalize_case`` /
    ``case_to_json``). Requires numpy (``pip install 'powerio[matrix]'``).
    """
    case = _load(path, content, json, format)
    try:
        d = case.to_dense()
    except ImportError as exc:
        raise ValueError(str(exc)) from exc
    except powerio.PowerIOError as exc:
        raise ValueError(f"dense view failed: {exc}") from exc
    return {
        "n": int(d.n),
        "m": int(d.m),
        "ng": int(d.ng),
        "base_mva": float(d.base_mva),
        "bus_ids": d.bus_ids.tolist(),
        "branch": {
            "from_id": d.branch.from_id.tolist(),
            "to_id": d.branch.to_id.tolist(),
            "r": d.branch.r.tolist(),
            "x": d.branch.x.tolist(),
            "b": d.branch.b.tolist(),
            "tap": d.branch.tap.tolist(),
            "shift": d.branch.shift.tolist(),
            "in_service": d.branch.in_service.tolist(),
        },
        "gen": {
            "bus": d.gen.bus.tolist(),
            "pg": d.gen.pg.tolist(),
            "pmax": d.gen.pmax.tolist(),
            "pmin": d.gen.pmin.tolist(),
            "in_service": d.gen.in_service.tolist(),
        },
        "demand": {"pd": d.demand.pd.tolist(), "qd": d.demand.qd.tolist()},
        "shunt": {"gs": d.shunt.gs.tolist(), "bs": d.shunt.bs.tolist()},
        "reference_bus": None if d.reference_bus is None else int(d.reference_bus),
        "n_components": int(d.n_components),
        "is_radial": bool(d.is_radial),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
