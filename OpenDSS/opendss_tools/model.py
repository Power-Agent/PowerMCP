"""Model-domain MCP tools."""

from typing import Any, Callable, Dict

from mcp.server.fastmcp import FastMCP
from py_dss_toolkit import dss_tools

from core import state
from utils.responses import _err, _ok, _require_circuit_loaded

# Maps internal table key -> accessor on dss_tools.model (dict-of-columns _records).
_TABLE_GETTERS: Dict[str, Callable[[Any], Any]] = {
    "summary": lambda m: m._summary_model_records,
    "buses": lambda m: m._buses_records,
    "lines": lambda m: m._lines_records,
    "transformers": lambda m: m._transformers_records,
    "meters": lambda m: m._meters_records,
    "monitors": lambda m: m._monitors_records,
    "generators": lambda m: m._generators_records,
    "vsources": lambda m: m._vsources_records,
    "regcontrols": lambda m: m._regcontrols_records,
    "loads": lambda m: m._loads_records,
    "pvsystems": lambda m: m._pvsystems_records,
    "storage": lambda m: m._storage_records,
    "segments": lambda m: m._segments_records,
    "segments_enabled": lambda m: m._enabled_segments_records,
    "segments_disabled": lambda m: m._disabled_segments_records,
    "pc_elements": lambda m: m._pc_elements_records,
    "pc_elements_enabled": lambda m: m._enabled_pc_elements_records,
    "pc_elements_disabled": lambda m: m._disabled_pc_elements_records,
    "pd_elements": lambda m: m._pd_elements_records,
    "pd_elements_enabled": lambda m: m._enabled_pd_elements_records,
    "pd_elements_disabled": lambda m: m._disabled_pd_elements_records,
} # TODO: add more table getters for other model tables when we add in py_dss_toolkit model


def _model_table_records(table_key: str) -> Dict[str, Any]:
    """Fetch one model table by internal key (used by explicit MCP tools only)."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    getter = _TABLE_GETTERS.get(table_key)
    if getter is None:
        return _err(f"Internal error: unknown table key {table_key!r}")
    try:
        rec = getter(dss_tools.model)
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


def get_model_summary_records() -> Dict[str, Any]:
    """Model summary counts and stats (model._summary_model_records). Requires a compiled circuit."""
    return _model_table_records("summary")


def get_buses_records() -> Dict[str, Any]:
    """Bus-level records for every bus (model._buses_records). Requires a compiled circuit."""
    return _model_table_records("buses")


def get_lines_records() -> Dict[str, Any]:
    """Line element records (model._lines_records). Payload is null if there are no lines. Requires a compiled circuit."""
    return _model_table_records("lines")


def get_transformers_records() -> Dict[str, Any]:
    """Transformer element records (model._transformers_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("transformers")


def get_meters_records() -> Dict[str, Any]:
    """EnergyMeter element records (model._meters_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("meters")


def get_monitors_records() -> Dict[str, Any]:
    """Monitor element records (model._monitors_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("monitors")


def get_generators_records() -> Dict[str, Any]:
    """Generator element records (model._generators_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("generators")


def get_vsources_records() -> Dict[str, Any]:
    """Vsource element records (model._vsources_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("vsources")


def get_regcontrols_records() -> Dict[str, Any]:
    """RegControl element records (model._regcontrols_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("regcontrols")


def get_loads_records() -> Dict[str, Any]:
    """Load element records (model._loads_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("loads")


def get_pvsystems_records() -> Dict[str, Any]:
    """PVSystem element records (model._pvsystems_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("pvsystems")


def get_storage_records() -> Dict[str, Any]:
    """Storage element records (model._storage_records). Payload is null if none. Requires a compiled circuit."""
    return _model_table_records("storage")


def get_segments_records() -> Dict[str, Any]:
    """Network segments (bus1 != bus2) records (model._segments_records). Requires a compiled circuit."""
    return _model_table_records("segments")


def get_enabled_segments_records() -> Dict[str, Any]:
    """Enabled segments only (model._enabled_segments_records). Requires a compiled circuit."""
    return _model_table_records("segments_enabled")


def get_disabled_segments_records() -> Dict[str, Any]:
    """Disabled segments only (model._disabled_segments_records). Requires a compiled circuit."""
    return _model_table_records("segments_disabled")


def get_pc_elements_records() -> Dict[str, Any]:
    """PC element records (model._pc_elements_records). Requires a compiled circuit."""
    return _model_table_records("pc_elements")


def get_enabled_pc_elements_records() -> Dict[str, Any]:
    """Enabled PC elements (model._enabled_pc_elements_records). Requires a compiled circuit."""
    return _model_table_records("pc_elements_enabled")


def get_disabled_pc_elements_records() -> Dict[str, Any]:
    """Disabled PC elements (model._disabled_pc_elements_records). Requires a compiled circuit."""
    return _model_table_records("pc_elements_disabled")


def get_pd_elements_records() -> Dict[str, Any]:
    """PD element records (model._pd_elements_records). Requires a compiled circuit."""
    return _model_table_records("pd_elements")


def get_enabled_pd_elements_records() -> Dict[str, Any]:
    """Enabled PD elements (model._enabled_pd_elements_records). Requires a compiled circuit."""
    return _model_table_records("pd_elements_enabled")


def get_disabled_pd_elements_records() -> Dict[str, Any]:
    """Disabled PD elements (model._disabled_pd_elements_records). Requires a compiled circuit."""
    return _model_table_records("pd_elements_disabled")


def get_element_data(element_class: str, element_name: str) -> Dict[str, Any]:
    """All DSS properties for one element as _element_data_records (dict of property -> one-element list).

    element_class: OpenDSS class (e.g. line, load, transformer).
    element_name: Object name only (e.g. for `line.l115`, use element_class='line', element_name='l115').
    Requires a compiled circuit.
    """
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        rec = dss_tools.model._element_data_records(element_class, element_name)
        return _ok(rec)
    except Exception as e:
        return _err(str(e))


def is_element_in_model(element_class: str, element_name: str) -> Dict[str, Any]:
    """Return whether `class.name` exists in the compiled circuit.

    element_class: OpenDSS class (e.g. line, load, transformer).
    element_name: Object name only (e.g. for `line.l115`, use element_class='line', element_name='l115').
    """
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        found = dss_tools.model.is_element_in_model(element_class, element_name)
        return _ok({"in_model": found})
    except Exception as e:
        return _err(str(e))


def edit_element(
    element_class: str, element_name: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Edit an existing element (DSS Edit-style). Clears solution snapshot.

    element_class: OpenDSS class (e.g. line, load, transformer).
    element_name: Object name only (e.g. `line.l115` -> element_class='line', element_name='l115').
    properties: Property name -> value as accepted by OpenDSS for that element.
    Requires a compiled circuit.
    """
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.edit_element(element_class, element_name, properties)
        state.solution_available = False
        return _ok({"edited": True, "element_class": element_class, "element_name": element_name})
    except Exception as e:
        return _err(str(e))


def add_element(
    element_class: str, element_name: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new element (DSS New-style). Clears solution snapshot.

    element_class: OpenDSS class (e.g. line, load, transformer).
    element_name: Name for the new object (e.g. new load `load.my_load` -> element_class='load', element_name='my_load').
    properties: Property name -> value as in a DSS New command.
    Requires a compiled circuit.
    """
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.add_element(element_class, element_name, properties)
        state.solution_available = False
        return _ok({"added": True, "element_class": element_class, "element_name": element_name})
    except Exception as e:
        return _err(str(e))


def disable_elements_by_type(element_type: str) -> Dict[str, Any]:
    """Disable all elements of a class (batchedit type..* enabled=false). Clears solution snapshot.

    element_type: OpenDSS class name only (e.g. load, line, transformer), same idea as element_class but applies to every element of that type.
    Requires a compiled circuit.
    """
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.disable_elements_type(element_type)
        state.solution_available = False
        return _ok({"disabled_type": element_type})
    except Exception as e:
        return _err(str(e))


def add_line_in_vsource(
    add_meter: bool = True,
    add_monitors: bool = False,
) -> Dict[str, Any]:
    """Insert feeder-head line at Vsource; optional energymeter and monitors (py-dss-toolkit model.add_line_in_vsource)."""
    err_response = _require_circuit_loaded()
    if err_response is not None:
        return err_response
    try:
        dss_tools.model.add_line_in_vsource(add_meter=add_meter, add_monitors=add_monitors)
        state.solution_available = False
        return _ok(
            {
                "added": True,
                "add_meter": add_meter,
                "add_monitors": add_monitors,
            }
        )
    except Exception as e:
        return _err(str(e))


def register_model_tools(mcp: FastMCP) -> None:
    mcp.tool()(get_model_summary_records)
    mcp.tool()(get_buses_records)
    mcp.tool()(get_lines_records)
    mcp.tool()(get_transformers_records)
    mcp.tool()(get_meters_records)
    mcp.tool()(get_monitors_records)
    mcp.tool()(get_generators_records)
    mcp.tool()(get_vsources_records)
    mcp.tool()(get_regcontrols_records)
    mcp.tool()(get_loads_records)
    mcp.tool()(get_pvsystems_records)
    mcp.tool()(get_storage_records)
    mcp.tool()(get_segments_records)
    mcp.tool()(get_enabled_segments_records)
    mcp.tool()(get_disabled_segments_records)
    mcp.tool()(get_pc_elements_records)
    mcp.tool()(get_enabled_pc_elements_records)
    mcp.tool()(get_disabled_pc_elements_records)
    mcp.tool()(get_pd_elements_records)
    mcp.tool()(get_enabled_pd_elements_records)
    mcp.tool()(get_disabled_pd_elements_records)
    mcp.tool()(get_element_data)
    mcp.tool()(is_element_in_model)
    mcp.tool()(edit_element)
    mcp.tool()(add_element)
    mcp.tool()(disable_elements_by_type)
    mcp.tool()(add_line_in_vsource)
