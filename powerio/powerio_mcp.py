"""PowerMCP's powerio conversion server: a thin re-export of the canonical
``powerio.mcp.server`` that ships with the powerio package.

powerio is a core dependency (see ``powermcp.registry`` / ``pyproject.toml``), so
this server keeps no copy of the conversion/summary/matrix tools. PowerIO is the
cross-server compiler layer for transmission and distribution cases:

- ``parse``: source format to canonical JSON or ``.pio.json`` package transport.
- ``convert`` / ``save``: canonical transport or source format to target artifact.
- ``summary``: canonical network summary.
- ``normalize``: normalized transmission transport.
- ``matrix``: sparse transmission matrix outputs.
- ``diagnostics``: structured diagnostics for ``.pio.json`` packages.
- ``display``: display artifacts such as PowerWorld ``.pwd`` geometry.

PowerMCP deliberately re-exports only those canonical tools. GridFM and PyPSA
folders route through ``parse`` and ``save`` with format names. OpenDSS compiles
DSS files produced by PowerIO when a distribution case needs that runtime.

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
diagnostics = _server.diagnostics
display = _server.display

__all__ = [
    "mcp",
    "convert",
    "save",
    "summary",
    "parse",
    "normalize",
    "matrix",
    "diagnostics",
    "display",
]


if __name__ == "__main__":
    mcp.run(transport="stdio")
