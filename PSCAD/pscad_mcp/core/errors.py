import asyncio
from enum import Enum
from typing import Any, Dict


class ErrorKind(str, Enum):
    LICENSE = "license"
    NOT_CONNECTED = "not_connected"
    FROZEN = "frozen"
    NOT_LOADED = "not_loaded"
    NOT_FOUND = "not_found"
    PARAM_INVALID = "param_invalid"
    TIMEOUT = "timeout"
    INTERNAL = "internal"


def classify_exception(exc: BaseException) -> ErrorKind:
    """Classify PSCAD exceptions into stable error kinds."""
    msg = str(exc).lower()

    if isinstance(exc, asyncio.TimeoutError):
        return ErrorKind.FROZEN

    if "frozen" in msg or "showing a dialog" in msg or "unresponsive" in msg:
        return ErrorKind.FROZEN
    if "pscad timed out" in msg:
        return ErrorKind.FROZEN

    if (
        "not connected" in msg
        or "not running on the system" in msg
        or "connection to pscad lost" in msg
    ):
        return ErrorKind.NOT_CONNECTED

    if "not licensed" in msg or "license" in msg:
        return ErrorKind.LICENSE

    if "project not found" in msg or "no such project" in msg:
        return ErrorKind.NOT_LOADED
    if "component not found" in msg or "no such component" in msg:
        return ErrorKind.NOT_FOUND

    if (
        "out of range" in msg
        or "not in legal range" in msg
        or "invalid value" in msg
        or "invalid parameter" in msg
    ):
        return ErrorKind.PARAM_INVALID

    if isinstance(exc, FileNotFoundError):
        return ErrorKind.NOT_FOUND

    return ErrorKind.INTERNAL


def ok(result: Any) -> Dict[str, Any]:
    return {"ok": True, "result": result, "error": None}


def err(kind: ErrorKind, detail: str) -> Dict[str, Any]:
    return {"ok": False, "result": None, "error": {"kind": kind.value, "detail": detail}}


def err_from_exc(exc: BaseException) -> Dict[str, Any]:
    return err(classify_exception(exc), str(exc))


def values_equivalent(requested: Any, stored: Any) -> bool:
    """Compare requested and stored PSCAD parameter values."""
    if requested == stored:
        return True
    if requested is None or stored is None:
        return False

    a, b = str(requested).strip(), str(stored).strip()
    if a == b:
        return True

    def strip_unit(s: str) -> str:
        idx = s.find("[")
        return s[:idx].strip() if idx > 0 else s.strip()

    a_no_unit = strip_unit(a)
    b_no_unit = strip_unit(b)
    if a_no_unit == b_no_unit:
        return True

    try:
        return abs(float(a_no_unit) - float(b_no_unit)) < 1e-9
    except (ValueError, TypeError):
        return False
