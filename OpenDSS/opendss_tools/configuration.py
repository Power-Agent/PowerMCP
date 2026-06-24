"""Configuration-domain MCP tools (compile, clear)."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from core.engine import dss
from utils.responses import _err, _ok


def compile_opendss_file(dss_file: str, force_recompile: bool = False) -> Dict[str, Any]:
    """Compile a master DSS file (ClearAll + Compile).

    If the same resolved path is already loaded, skips compile unless ``force_recompile`` is True
    (e.g. user wants to recompile the model to clean changes). A different ``dss_file`` loads a new model and always compiles.
    After ``clear_all_opendss_memory``, the next call compiles as usual.

    Returns dss_file, circuit_readiness, circuit_loaded, and whether the compile was skipped.
    """
    resolved = str(Path(dss_file).resolve())
    if (
        state.circuit_loaded
        and state.last_compiled_dss_file is not None
        and resolved == state.last_compiled_dss_file
        and not force_recompile
    ):
        readiness = dss_tools.configuration.circuit_readiness()
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": True,
                "already_compiled": True,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": state.solution_available,
            }
        )
    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness = dss_tools.configuration.circuit_readiness()
        state.circuit_loaded = True
        state.solution_available = False
        state.last_compiled_dss_file = resolved
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": False,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as e:
        state.circuit_loaded = False
        state.solution_available = False
        state.last_compiled_dss_file = None
        return _err(str(e))


def compile_distribution(
    path: Optional[str] = None,
    content: Optional[str] = None,
    source_format: Optional[str] = None,
    format: Optional[str] = None,
    force_recompile: bool = False,
) -> Dict[str, Any]:
    """Compile a distribution case given in any powerio distribution format.

    The on-ramp into OpenDSS for the BMOPF and PowerModelsDistribution worlds: a
    feeder held as IEEE BMOPF JSON (``bmopf-json``), PowerModelsDistribution
    ENGINEERING JSON (``pmd-json``), or already as OpenDSS ``.dss`` is converted
    to a self-contained ``.dss`` file by powerio and compiled here, so a case
    authored or solved in those toolchains can run in OpenDSS without a hand
    translation.

    Provide exactly one of ``path`` (a file on disk) or ``content`` (inline file
    text). ``source_format``/``format`` is the distribution format name
    (``dss``, ``pmd-json``, ``bmopf-json``); for a ``path`` it is inferred from
    the extension when omitted, but it is REQUIRED for inline ``content``.

    Returns the ``compile_opendss_file`` result plus ``staged_dss_file`` (the
    converted ``.dss`` path on disk, or ``None`` when an original DSS path was
    compiled directly) and ``conversion_warnings`` (powerio's fidelity notes for
    the BMOPF/PMD -> OpenDSS conversion, such as solver metadata OpenDSS cannot
    represent).
    """
    try:
        import powerio.dist as _dist
    except ImportError as exc:  # pragma: no cover - powerio is a core dependency
        return _err(f"powerio is required to convert distribution cases: {exc}")

    if (path is None) == (content is None):
        return _err("provide exactly one of `path` or `content`")
    source_key = (
        source_format.strip().lower().replace("_", "-") if source_format else None
    )
    format_key = format.strip().lower().replace("_", "-") if format else None
    if source_key is not None and format_key is not None and source_key != format_key:
        return _err("`source_format` and `format` disagree")
    source_key = source_key or format_key
    if content is not None and not source_key:
        return _err("`format` is required when compiling inline `content`")

    direct_dss = (
        path is not None
        and (
            source_key in ("dss", "opendss")
            or (source_key is None and Path(path).suffix.lower() == ".dss")
        )
    )
    if direct_dss:
        result = compile_opendss_file(path, force_recompile=force_recompile)
        if isinstance(result, dict):
            target = (
                result["payload"] if isinstance(result.get("payload"), dict) else result
            )
            target["staged_dss_file"] = None
            target["distribution_source_file"] = path
            target["conversion_warnings"] = []
        return result

    try:
        if path is not None:
            conv = _dist.convert_file(path, "dss", source_key)
        else:
            conv = _dist.convert_str(content, "dss", source_key)
    except FileNotFoundError as exc:
        return _err(f"file not found: {exc}")
    except OSError as exc:
        return _err(f"cannot read file: {exc}")
    except Exception as exc:  # powerio.PowerIOError and friends use one error shape
        return _err(f"distribution conversion failed: {exc}")

    # newline="" keeps the converter output byte-identical across platforms.
    fd, staged = tempfile.mkstemp(suffix=".dss", prefix="powerio_dist_")
    try:
        with open(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(conv.text)
    except OSError as exc:
        try:  # don't leave a 0-byte temp behind on a failed stage
            os.unlink(staged)
        except OSError:
            pass
        return _err(f"failed to stage .dss file: {exc}")

    result = compile_opendss_file(staged, force_recompile=force_recompile)
    if isinstance(result, dict):
        # Sit beside the rest of the compile result inside the _ok payload.
        target = (
            result["payload"] if isinstance(result.get("payload"), dict) else result
        )
        target["staged_dss_file"] = staged
        target["distribution_source_file"] = path
        target["conversion_warnings"] = list(conv.warnings)
    return result


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory (ClearAll); resets circuit_loaded, solution_available, and last compiled path."""
    try:
        dss.text("ClearAll")
        state.circuit_loaded = False
        state.solution_available = False
        state.last_compiled_dss_file = None
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as e:
        return _err(str(e))


def register_configuration_tools(mcp: FastMCP) -> None:
    mcp.tool()(compile_opendss_file)
    mcp.tool()(compile_distribution)
    mcp.tool()(clear_all_opendss_memory)
