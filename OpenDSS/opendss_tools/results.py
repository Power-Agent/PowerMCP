"""Results-domain MCP tools (snapshot power-flow results)."""

from typing import Any, Callable, Dict, Optional

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from utils.responses import _err, _ok, _require_solution

_VALID_CURRENT_LIMIT_TYPES = frozenset({"norm_amps", "emerg_amps"})


def _other_current_limit_type(current_limit_type: str) -> str:
    return "emerg_amps" if current_limit_type == "norm_amps" else "norm_amps"


def _validate_current_limit_type(current_limit_type: str) -> Optional[Dict[str, Any]]:
    if current_limit_type not in _VALID_CURRENT_LIMIT_TYPES:
        return _err(
            "current_limit_type must be 'norm_amps' or 'emerg_amps'; "
            f"got {current_limit_type!r}"
        )
    return None


def _current_limit_tool_note(kind: str, current_limit_type: str) -> str:
    other = _other_current_limit_type(current_limit_type)
    return (
        f"{kind} uses {current_limit_type} as the amp limit for this call. "
        f"Pass current_limit_type={other!r} on a future call to use the other limit. "
        "This updates the py-dss-toolkit session-wide setting until changed again."
    )


_DEFAULT_VIOLATION_V_MIN_PU = 0.95
_DEFAULT_VIOLATION_V_MAX_PU = 1.05


def _validate_voltage_pu_limits(
    v_min_pu: float, v_max_pu: float
) -> Optional[Dict[str, Any]]:
    if v_min_pu >= v_max_pu:
        return _err(
            "v_min_pu must be less than v_max_pu; "
            f"got v_min_pu={v_min_pu!r}, v_max_pu={v_max_pu!r}"
        )
    return None


def _voltage_violation_tool_note(kind: str, v_min_pu: float, v_max_pu: float) -> str:
    return (
        f"{kind} use v_min_pu={v_min_pu} and v_max_pu={v_max_pu} for this call "
        "(set via set_violation_voltage_ln_limits; applies to LN, LL, and smart "
        "nodal violation reads). Pass different v_min_pu/v_max_pu on a future call "
        "to change limits. This updates the py-dss-toolkit session-wide setting "
        "until changed again."
    )


def _violation_voltage_payload(
    records_attr: str,
    kind: str,
    v_min_pu: float,
    v_max_pu: float,
) -> Dict[str, Any]:
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    bad = _validate_voltage_pu_limits(v_min_pu, v_max_pu)
    if bad is not None:
        return bad
    try:
        dss_tools.results.set_violation_voltage_ln_limits(
            v_min_pu=v_min_pu, v_max_pu=v_max_pu
        )
        rec = getattr(dss_tools.results, records_attr)
        return _ok(
            {
                "records": rec,
                "v_min_pu": v_min_pu,
                "v_max_pu": v_max_pu,
                "note": _voltage_violation_tool_note(kind, v_min_pu, v_max_pu),
            }
        )
    except Exception as e:
        return _err(str(e))


# Snapshot keys -> accessor on dss_tools.results (mostly _records).
_RESULTS_GETTERS: Dict[str, Callable[[Any], Any]] = {
    "summary": lambda r: r._summary_records,
    "voltage_mag_ln_nodes": lambda r: r._voltage_mag_ln_nodes_records,
    "voltage_ang_ln_nodes": lambda r: r._voltage_ang_ln_nodes_records,
    "voltage_mag_ll_nodes": lambda r: r._voltage_mag_ll_nodes_records,
    "voltage_ang_ll_nodes": lambda r: r._voltage_ang_ll_nodes_records,
    "voltage_mag_smart_nodes": lambda r: r._voltage_mag_smart_nodes_records,
    "voltage_ang_smart_nodes": lambda r: r._voltage_ang_smart_nodes_records,
    "powers_p": lambda r: r._powers_p_records,
    "powers_q": lambda r: r._powers_q_records,
    "losses_p": lambda r: r._losses_p_records,
    "losses_q": lambda r: r._losses_q_records,
    "currents_element_mag": lambda r: r._currents_element_mag_records,
    "currents_element_ang": lambda r: r._currents_element_ang_records,
    "currents_element_norm_amps": lambda r: r._currents_element_norm_amps_records,
    "currents_element_emerg_amps": lambda r: r._currents_element_emerg_amps_records,
    "voltages_element_mag": lambda r: r._voltages_element_mag_records,
    "voltages_element_ang": lambda r: r._voltages_element_ang_records,
    "all_losses": lambda r: r._all_losses_records,
}


def _snapshot_records(key: str) -> Dict[str, Any]:
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    getter = _RESULTS_GETTERS.get(key)
    if getter is None:
        return _err(f"Internal error: unknown results key {key!r}")
    try:
        rec = getter(dss_tools.results)
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


def get_results_summary_records() -> Dict[str, Any]:
    """Feeder summary after solve (results._summary_records). Requires a snapshot solution."""
    return _snapshot_records("summary")


def get_voltage_mag_ln_nodes_records() -> Dict[str, Any]:
    """Line-to-neutral nodal voltage magnitudes (results._voltage_mag_ln_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_mag_ln_nodes")


def get_voltage_ang_ln_nodes_records() -> Dict[str, Any]:
    """Line-to-neutral nodal voltage angles (results._voltage_ang_ln_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_ang_ln_nodes")


def get_voltage_mag_ll_nodes_records() -> Dict[str, Any]:
    """Line-to-line nodal voltage magnitudes (results._voltage_mag_ll_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_mag_ll_nodes")


def get_voltage_ang_ll_nodes_records() -> Dict[str, Any]:
    """Line-to-line nodal voltage angles (results._voltage_ang_ll_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_ang_ll_nodes")


def get_voltage_mag_smart_nodes_records() -> Dict[str, Any]:
    """Smart nodal voltage magnitudes per bus. LN/LL is selected based on the transformer connection type that feeds the bus (results._voltage_mag_smart_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_mag_smart_nodes")


def get_voltage_ang_smart_nodes_records() -> Dict[str, Any]:
    """Smart nodal voltage angles per bus. LN/LL is selected based on the transformer connection type that feeds the bus (results._voltage_ang_smart_nodes_records). Requires a snapshot solution."""
    return _snapshot_records("voltage_ang_smart_nodes")


def get_powers_p_records() -> Dict[str, Any]:
    """Real power P by PD element (results._powers_p_records). Requires a snapshot solution."""
    return _snapshot_records("powers_p")


def get_powers_q_records() -> Dict[str, Any]:
    """Reactive power Q by PD element (results._powers_q_records). Requires a snapshot solution."""
    return _snapshot_records("powers_q")


def get_losses_p_records() -> Dict[str, Any]:
    """Real power losses P by PD element (results._losses_p_records). Requires a snapshot solution."""
    return _snapshot_records("losses_p")


def get_losses_q_records() -> Dict[str, Any]:
    """Reactive power losses Q by PD element (results._losses_q_records). Requires a snapshot solution."""
    return _snapshot_records("losses_q")


def get_currents_element_mag_records() -> Dict[str, Any]:
    """Current magnitudes by element (results._currents_element_mag_records). Requires a snapshot solution."""
    return _snapshot_records("currents_element_mag")


def get_currents_element_ang_records() -> Dict[str, Any]:
    """Current angles by element (results._currents_element_ang_records). Requires a snapshot solution."""
    return _snapshot_records("currents_element_ang")


def get_currents_element_norm_amps_records() -> Dict[str, Any]:
    """Norm amps per element (results._currents_element_norm_amps_records). Requires a snapshot solution."""
    return _snapshot_records("currents_element_norm_amps")


def get_currents_element_emerg_amps_records() -> Dict[str, Any]:
    """Emergency amps per element (results._currents_element_emerg_amps_records). Requires a snapshot solution."""
    return _snapshot_records("currents_element_emerg_amps")


def get_voltages_element_mag_records() -> Dict[str, Any]:
    """Element voltage magnitudes (results._voltages_element_mag_records). Requires a snapshot solution."""
    return _snapshot_records("voltages_element_mag")


def get_voltages_element_ang_records() -> Dict[str, Any]:
    """Element voltage angles (results._voltages_element_ang_records). Requires a snapshot solution."""
    return _snapshot_records("voltages_element_ang")


def get_all_losses_records() -> Dict[str, Any]:
    """All-losses breakdown per PD element (results._all_losses_records: tuple of element dict and order list). Requires a snapshot solution."""
    return _snapshot_records("all_losses")


def get_violation_voltage_ln_nodes_records(
    v_min_pu: float = _DEFAULT_VIOLATION_V_MIN_PU,
    v_max_pu: float = _DEFAULT_VIOLATION_V_MAX_PU,
) -> Dict[str, Any]:
    """LN undervoltage/overvoltage nodal violations (results._violation_voltage_ln_nodes_records).

    v_min_pu / v_max_pu default to 0.95 / 1.04 and are applied via
    set_violation_voltage_ln_limits before reading (same global limits as LL and smart
    nodal violation tools). Payload includes records, the limits used, and a short note.
    Requires a snapshot solution.
    """
    return _violation_voltage_payload(
        "_violation_voltage_ln_nodes_records",
        "LN nodal voltage violations",
        v_min_pu,
        v_max_pu,
    )


def get_violation_voltage_ll_nodes_records(
    v_min_pu: float = _DEFAULT_VIOLATION_V_MIN_PU,
    v_max_pu: float = _DEFAULT_VIOLATION_V_MAX_PU,
) -> Dict[str, Any]:
    """LL undervoltage/overvoltage nodal violations (results._violation_voltage_ll_nodes_records).

    v_min_pu / v_max_pu default to 0.95 / 1.04 and are applied via
    set_violation_voltage_ln_limits before reading. Payload includes records, the
    limits used, and a short note. Requires a snapshot solution.
    """
    return _violation_voltage_payload(
        "_violation_voltage_ll_nodes_records",
        "LL nodal voltage violations",
        v_min_pu,
        v_max_pu,
    )


def get_violation_voltage_nodes_records(
    v_min_pu: float = _DEFAULT_VIOLATION_V_MIN_PU,
    v_max_pu: float = _DEFAULT_VIOLATION_V_MAX_PU,
) -> Dict[str, Any]:
    """Smart LN/LL undervoltage/overvoltage nodal violations (results._violation_voltage_nodes_records).

    v_min_pu / v_max_pu default to 0.95 / 1.04 and are applied via
    set_violation_voltage_ln_limits before reading. Payload includes records, the
    limits used, and a short note. Requires a snapshot solution.
    """
    return _violation_voltage_payload(
        "_violation_voltage_nodes_records",
        "Smart nodal voltage violations",
        v_min_pu,
        v_max_pu,
    )


def get_current_loading_percent_records(
    current_limit_type: str = "norm_amps",
) -> Dict[str, Any]:
    """Thermal loading percent by element (results._current_loading_percent_records).

    current_limit_type: 'norm_amps' (default) or 'emerg_amps'; sets the session amp limit before reading.
    Payload includes records, which limit was used, the other option, and a short note.
    Requires a snapshot solution.
    """
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    bad = _validate_current_limit_type(current_limit_type)
    if bad is not None:
        return bad
    try:
        dss_tools.results.set_violation_current_limit_type(current_limit_type)
        rec = dss_tools.results._current_loading_percent_records
        return _ok(
            {
                "records": rec,
                "current_limit_type": current_limit_type,
                "other_limit_type": _other_current_limit_type(current_limit_type),
                "note": _current_limit_tool_note("Loading percent", current_limit_type),
            }
        )
    except Exception as e:
        return _err(str(e))


def get_violation_currents_elements_records(
    current_limit_type: str = "norm_amps",
) -> Dict[str, Any]:
    """Elements exceeding the loading threshold (results._violation_currents_elements_records).

    current_limit_type: 'norm_amps' (default) or 'emerg_amps'; sets the session amp limit before reading.
    Payload includes records, which limit was used, the other option, and a short note.
    Requires a snapshot solution.
    """
    err_response = _require_solution()
    if err_response is not None:
        return err_response
    bad = _validate_current_limit_type(current_limit_type)
    if bad is not None:
        return bad
    try:
        dss_tools.results.set_violation_current_limit_type(current_limit_type)
        rec = dss_tools.results._violation_currents_elements_records
        return _ok(
            {
                "records": rec,
                "current_limit_type": current_limit_type,
                "other_limit_type": _other_current_limit_type(current_limit_type),
                "note": _current_limit_tool_note(
                    "Thermal violation elements", current_limit_type
                ),
            }
        )
    except Exception as e:
        return _err(str(e))


def register_results_tools(mcp: FastMCP) -> None:
    mcp.tool()(get_results_summary_records)
    mcp.tool()(get_voltage_mag_ln_nodes_records)
    mcp.tool()(get_voltage_ang_ln_nodes_records)
    mcp.tool()(get_voltage_mag_ll_nodes_records)
    mcp.tool()(get_voltage_ang_ll_nodes_records)
    mcp.tool()(get_voltage_mag_smart_nodes_records)
    mcp.tool()(get_voltage_ang_smart_nodes_records)
    mcp.tool()(get_powers_p_records)
    mcp.tool()(get_powers_q_records)
    mcp.tool()(get_losses_p_records)
    mcp.tool()(get_losses_q_records)
    mcp.tool()(get_currents_element_mag_records)
    mcp.tool()(get_currents_element_ang_records)
    mcp.tool()(get_currents_element_norm_amps_records)
    mcp.tool()(get_currents_element_emerg_amps_records)
    mcp.tool()(get_voltages_element_mag_records)
    mcp.tool()(get_voltages_element_ang_records)
    mcp.tool()(get_all_losses_records)
    mcp.tool()(get_violation_voltage_ln_nodes_records)
    mcp.tool()(get_violation_voltage_ll_nodes_records)
    mcp.tool()(get_violation_voltage_nodes_records)
    mcp.tool()(get_current_loading_percent_records)
    mcp.tool()(get_violation_currents_elements_records)
