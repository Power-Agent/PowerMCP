"""PowerMCP's powerio conversion server — a thin re-export of the canonical
``powerio.mcp.server`` that ships with the powerio package.

powerio is a core dependency (see ``powermcp.registry`` / ``pyproject.toml``), so
this server keeps no copy of the conversion/summary/matrix tools: it re-exports
the canonical FastMCP ``mcp`` instance and every tool registered on it. As of
powerio 0.3.3 the surface is the bare powerio verbs, one set for transmission
and distribution (routed by format):

- ``convert`` / ``save`` / ``summary`` — any single-file format, either domain.
  ``save(to="dss")`` stages an IEEE BMOPF or PowerModelsDistribution case as a
  ``.dss`` file the OpenDSS server can compile (see its
  ``compile_distribution`` tool); ``save(to="pypsa-csv")`` writes the CSV folder.
- ``parse`` / ``to_json`` / ``normalize`` / ``compute_matrix`` / ``dense_view`` —
  transmission only (a distribution network has no JSON transport and isn't
  positive-sequence).
- ``read_gridfm`` / ``write_gridfm`` — the gridfm Parquet dataset;
  ``read_display_file`` — PowerWorld ``.pwd`` one-line geometry.

These stay in lockstep with powerio, nothing to hand-sync. The previous
``read_display_file`` overlay was upstreamed in powerio 0.3.3 and is gone, so
this module is now a pure re-export. powerio also still registers the pre-0.3.3
aliases (``*_case``, ``read_pypsa_csv_folder``, ``write_pypsa_csv_folder``),
deprecated and removed in powerio 0.4.0; they ride along on the ``mcp`` instance
but new PowerMCP code uses the bare verbs.

Run over stdio with ``python powerio_mcp.py`` (or ``powermcp run powerio``).
"""

from __future__ import annotations

# Re-export the canonical server and its tools verbatim. Importing
# ``powerio.mcp.server`` also fails loudly if the repo's own ``powerio/``
# directory shadows the installed package (it has no ``mcp`` submodule), so no
# separate shadow guard is needed.
from powerio.mcp.server import (  # noqa: F401  (re-exported for `powermcp run` and tests)
    mcp,
    convert,
    save,
    summary,
    parse,
    to_json,
    normalize,
    compute_matrix,
    dense_view,
    read_gridfm,
    write_gridfm,
    read_display_file,
)


if __name__ == "__main__":
    mcp.run(transport="stdio")
