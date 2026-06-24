"""PowerMCP's powerio conversion server: a thin re-export of the canonical
``powerio.mcp.server`` that ships with the powerio package.

powerio is a core dependency (see ``powermcp.registry`` / ``pyproject.toml``), so
this server keeps no copy of the conversion/summary/matrix tools. As of powerio
0.3.3 the canonical MCP surface is the bare powerio verbs, one set for
transmission and distribution (routed by format):

- ``convert`` / ``save`` / ``summary``: generic format and transport verbs.
  ``save(to="dss")`` stages an IEEE BMOPF or PowerModelsDistribution case as a
  ``.dss`` file the OpenDSS server can compile (see its
  ``compile_distribution`` tool); ``save(to="pypsa-csv")`` writes the CSV folder.
- ``parse`` / ``normalize``: JSON transport for parsed or normalized networks.
- ``matrix``: sparse transmission matrix outputs.
- ``display``: display artifacts such as PowerWorld ``.pwd`` geometry.

PowerMCP deliberately re-exports only those canonical tools. GridFM and PyPSA
folders route through ``parse`` and ``save`` with format names, and display
artifacts route through ``display``.

Run over stdio with ``python powerio_mcp.py`` (or ``powermcp run powerio``).
"""

from __future__ import annotations

from powerio.mcp import server as _server

mcp = _server.mcp
convert = _server.convert
save = _server.save
summary = _server.summary
parse = _server.parse
normalize = _server.normalize
matrix = _server.matrix
display = _server.display

__all__ = [
    "mcp",
    "convert",
    "save",
    "summary",
    "parse",
    "normalize",
    "matrix",
    "display",
]


if __name__ == "__main__":
    mcp.run(transport="stdio")
