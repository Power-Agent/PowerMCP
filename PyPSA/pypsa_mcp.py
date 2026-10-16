import sys
import os
import inspect
import tempfile
from mcp.server.mcpserver import MCPServer as FastMCP
from pypsa import Network
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.solver_case import resolve_solver_case, diagnostic_messages
    from powermcp.sandbox import (
        PathNotAllowed,
        checked_path,
        checked_read_tree,
        staged_directory_write,
    )
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added


def _to_serializable(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    if hasattr(obj, 'tolist'):  # numpy array
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(x) for x in obj]
    if hasattr(obj, 'strftime'):  # datetime-like
        return str(obj)
    if hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj


# Create an MCP server
mcp = FastMCP("PyPSA-MCP")


def _checked_network_source(value: str, *, purpose: str) -> str:
    """Preflight a NetCDF file or every descendant of a CSV directory."""
    return checked_read_tree(value, purpose=purpose)


def _optimize(network: Network, **kwargs):
    """Call the modern optimizer with stable semantics across supported PyPSA.

    ``include_objective_constant`` is not present throughout the supported
    pre-2 range, and PyPSA plans to change its default in 2.0. Pass today's
    behavior explicitly whenever the installed accessor supports it.
    """
    parameters = inspect.signature(network.optimize.__call__).parameters
    if "include_objective_constant" in parameters:
        kwargs["include_objective_constant"] = True
    return network.optimize(**kwargs)


# ============= Network Information =============

@mcp.tool()
def get_network_info(network_name: str) -> Dict[str, Any]:
    """Get basic information about the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    info = {
        "buses": len(network.buses),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "lines": len(network.lines),
        "transformers": len(network.transformers),
        "storage_units": len(network.storage_units),
        "snapshots": len(network.snapshots),
        "components": list(network.all_components)
    }
    return info

@mcp.tool()
def load_network(file_path: str) -> Dict[str, Any]:
    """Load a PyPSA network from a NetCDF (.nc) file"""
    try:
        file_path = _checked_network_source(file_path, purpose="file_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        network = Network(file_path)
        info = {
            "buses": len(network.buses),
            "generators": len(network.generators),
            "loads": len(network.loads),
            "lines": len(network.lines),
            "transformers": len(network.transformers),
            "snapshots": len(network.snapshots),
        }
        return {
            "status": "success",
            "message": f"Network loaded successfully from {file_path}",
            "info": info
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to load network: {str(e)}"
        }

@mcp.tool()
def run_power_flow(network_name: str, linear: bool = False) -> Dict[str, Any]:
    """Run a non-linear (AC) or linear (DC) power flow on the network"""
    try:
        network_name = _checked_network_source(network_name, purpose="network_name")
        network = Network(network_name)
        
        if linear:
            network.lpf()
        else:
            network.pf()
            
        # Get basic results
        results = {
            "status": "success",
            "message": f"{'Linear' if linear else 'Non-linear'} power flow completed successfully.",
            "buses": {},
            "lines": {}
        }
        
        for bus in network.buses.index:
            bus_data = {}
            if not network.buses_t.v_mag_pu.empty and bus in network.buses_t.v_mag_pu:
                bus_data["v_mag_pu"] = network.buses_t.v_mag_pu[bus].tolist() if len(network.snapshots) > 1 else float(network.buses_t.v_mag_pu[bus].iloc[0])
            if not network.buses_t.v_ang.empty and bus in network.buses_t.v_ang:
                bus_data["v_ang"] = network.buses_t.v_ang[bus].tolist() if len(network.snapshots) > 1 else float(network.buses_t.v_ang[bus].iloc[0])
            results["buses"][bus] = bus_data
            
        for line in network.lines.index:
            line_data = {}
            if not network.lines_t.p0.empty and line in network.lines_t.p0:
                line_data["p0"] = network.lines_t.p0[line].tolist() if len(network.snapshots) > 1 else float(network.lines_t.p0[line].iloc[0])
            if not network.lines_t.q0.empty and line in network.lines_t.q0:
                line_data["q0"] = network.lines_t.q0[line].tolist() if len(network.snapshots) > 1 else float(network.lines_t.q0[line].iloc[0])
            results["lines"][line] = line_data
            
        return _to_serializable(results)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Power flow failed: {str(e)}"
        }

@mcp.tool()
def run_contingency_analysis(
    network_name: str,
    contingency_elements: Optional[List[str]] = None,
    v_min_pu: float = 0.95,
    v_max_pu: float = 1.05,
    line_max_loading_pct: float = 100.0,
) -> Dict[str, Any]:
    """Run N-1 contingency analysis on the network.

    Outages each line/transformer one at a time, runs AC power flow,
    and checks for voltage and thermal violations.
    """
    try:
        # --- Base case ---
        network_name = _checked_network_source(network_name, purpose="network_name")
        network = Network(network_name)
        network.pf(use_seed=True)

        base_v = network.buses_t.v_mag_pu.iloc[0]
        base_p0 = network.lines_t.p0.iloc[0]
        base_q0 = network.lines_t.q0.iloc[0]
        base_s_nom = network.lines.s_nom
        base_loading = np.sqrt(base_p0**2 + base_q0**2) / base_s_nom * 100
        base_loading = base_loading.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        base_case = {
            "converged": True,
            "min_voltage_pu": float(base_v.min()),
            "max_voltage_pu": float(base_v.max()),
            "max_line_loading_pct": float(base_loading.max()),
        }

        # --- Determine contingency elements ---
        if contingency_elements is None:
            elements = []
            for line_id in network.lines.index:
                elements.append(("line", line_id))
            for trafo_id in network.transformers.index:
                elements.append(("transformer", trafo_id))
        else:
            elements = []
            for elem_id in contingency_elements:
                if elem_id in network.lines.index:
                    elements.append(("line", elem_id))
                elif elem_id in network.transformers.index:
                    elements.append(("transformer", elem_id))
                else:
                    return {
                        "status": "error",
                        "message": f"Element '{elem_id}' not found in lines or transformers",
                    }

        # --- Run contingencies ---
        contingencies = []
        non_converged = 0
        with_violations = 0

        for elem_type, elem_id in elements:
            n = Network(network_name)

            if elem_type == "line":
                n.lines.at[elem_id, "active"] = False
            else:
                n.transformers.at[elem_id, "active"] = False

            try:
                pf_result = n.pf(use_seed=True)
                converged = bool(pf_result["converged"].iloc[0, 0])
            except Exception:
                converged = False

            if not converged:
                non_converged += 1
                contingencies.append({
                    "id": elem_id,
                    "element_type": elem_type,
                    "converged": False,
                    "voltage_violations": [],
                    "loading_violations": [],
                })
                with_violations += 1
                continue

            # Check voltage violations
            v_mag = n.buses_t.v_mag_pu.iloc[0]
            voltage_violations = []
            for bus in v_mag.index:
                v = float(v_mag[bus])
                if v < v_min_pu or v > v_max_pu:
                    voltage_violations.append({"bus": bus, "vm_pu": round(v, 4)})

            # Check thermal violations
            p0 = n.lines_t.p0.iloc[0]
            q0 = n.lines_t.q0.iloc[0]
            s_nom = n.lines.s_nom
            loading = np.sqrt(p0**2 + q0**2) / s_nom * 100
            loading = loading.replace([np.inf, -np.inf], np.nan).fillna(0.0)

            loading_violations = []
            for line_id_inner in loading.index:
                pct = float(loading[line_id_inner])
                if pct > line_max_loading_pct:
                    loading_violations.append({
                        "line": line_id_inner,
                        "loading_pct": round(pct, 2),
                    })

            has_violations = len(voltage_violations) > 0 or len(loading_violations) > 0
            if has_violations:
                with_violations += 1

            contingencies.append({
                "id": elem_id,
                "element_type": elem_type,
                "converged": True,
                "voltage_violations": voltage_violations,
                "loading_violations": loading_violations,
            })

        total = len(elements)
        return _to_serializable({
            "status": "success",
            "message": f"N-1 contingency analysis completed. {with_violations} of {total} contingencies have violations.",
            "base_case": base_case,
            "contingencies": contingencies,
            "summary": {
                "total_contingencies": total,
                "with_violations": with_violations,
                "non_converged": non_converged,
            },
        })
    except Exception as e:
        return {
            "status": "error",
            "message": f"Contingency analysis failed: {str(e)}",
        }


@mcp.tool()
def get_component_details(
    network_name: str,
    component_type: str,
    component_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get detailed information about a specific component or all components of a type"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    
    if not hasattr(network, component_type):
        return {
            "status": "error",
            "message": f"Component type '{component_type}' not found"
        }
    
    component_df = getattr(network, component_type)
    
    if component_id:
        if component_id not in component_df.index:
            return {
                "status": "error",
                "message": f"Component '{component_id}' not found in {component_type}"
            }
        result = component_df.loc[component_id].to_dict()
    else:
        result = component_df.to_dict('index')

    return _to_serializable(result)

# ============= Network Construction =============

@mcp.tool()
def create_network(
    name: str = "network",
    snapshots: Optional[List[str]] = None,
    crs: str = "EPSG:4326"
) -> Dict[str, Any]:
    """Create a new PyPSA network"""
    network_kwargs: Dict[str, Any] = {"name": name, "crs": crs}
    if snapshots is not None:
        network_kwargs["snapshots"] = pd.DatetimeIndex(snapshots)
    network = Network(**network_kwargs)
    output_path = checked_path(
        f"{name}.nc", purpose="generated network path", for_write=True
    )
    network.export_to_netcdf(output_path)
    return {
        "status": "success",
        "message": f"Network '{name}' created and saved to {output_path}",
        "network_file": output_path,
    }

@mcp.tool()
def add_bus(
    network_name: str,
    bus_id: str,
    v_nom: float = 380.0,
    x: Optional[float] = None,
    y: Optional[float] = None,
    carrier: str = "AC"
) -> Dict[str, Any]:
    """Add a bus to the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    network.add("Bus", bus_id, v_nom=v_nom, x=x, y=y, carrier=carrier)
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Bus '{bus_id}' added to network"
    }

@mcp.tool()
def add_generator(
    network_name: str,
    gen_id: str,
    bus: str,
    p_nom: float,
    marginal_cost: float = 0.0,
    carrier: str = "generator",
    p_min_pu: float = 0.0,
    p_max_pu: float = 1.0
) -> Dict[str, Any]:
    """Add a generator to the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    network.add(
        "Generator",
        gen_id,
        bus=bus,
        p_nom=p_nom,
        marginal_cost=marginal_cost,
        carrier=carrier,
        p_min_pu=p_min_pu,
        p_max_pu=p_max_pu
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Generator '{gen_id}' added to network"
    }

@mcp.tool()
def add_load(
    network_name: str,
    load_id: str,
    bus: str,
    p_set: float
) -> Dict[str, Any]:
    """Add a load to the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    network.add("Load", load_id, bus=bus, p_set=p_set)
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Load '{load_id}' added to network"
    }

@mcp.tool()
def add_line(
    network_name: str,
    line_id: str,
    bus0: str,
    bus1: str,
    x: float,
    r: float = 0.0,
    s_nom: float = 1000.0,
    length: float = 1.0
) -> Dict[str, Any]:
    """Add a transmission line to the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    network.add(
        "Line",
        line_id,
        bus0=bus0,
        bus1=bus1,
        x=x,
        r=r,
        s_nom=s_nom,
        length=length
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Line '{line_id}' added to network"
    }

@mcp.tool()
def add_storage_unit(
    network_name: str,
    storage_id: str,
    bus: str,
    p_nom: float,
    max_hours: float = 6.0,
    efficiency_store: float = 0.9,
    efficiency_dispatch: float = 0.9,
    cyclic_state_of_charge: bool = True
) -> Dict[str, Any]:
    """Add a storage unit to the network"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    network.add(
        "StorageUnit",
        storage_id,
        bus=bus,
        p_nom=p_nom,
        max_hours=max_hours,
        efficiency_store=efficiency_store,
        efficiency_dispatch=efficiency_dispatch,
        cyclic_state_of_charge=cyclic_state_of_charge
    )
    network.export_to_netcdf(network_name)
    return {
        "status": "success",
        "message": f"Storage unit '{storage_id}' added to network"
    }

# ============= Optimization =============

@mcp.tool()
def optimize_network(
    network_name: str,
    solver_name: str = "highs",
    formulation: str = "kirchhoff",
    pyomo: bool = False,
    solver_options: Optional[Dict] = None
) -> Dict[str, Any]:
    """Run a linear optimal power flow on the network.

    Modern PyPSA uses its Linopy-backed ``Network.optimize`` accessor.  The
    legacy ``formulation`` and ``pyomo`` arguments remain in the MCP schema so
    existing clients do not break, but only PyPSA's current Kirchhoff/Linopy
    path is available.
    """
    network_name = _checked_network_source(network_name, purpose="network_name")
    if formulation != "kirchhoff":
        return {
            "status": "error",
            "message": (
                "Modern PyPSA supports the 'kirchhoff' formulation through "
                "Network.optimize; other legacy LOPF formulations are unavailable."
            ),
        }
    if pyomo:
        return {
            "status": "error",
            "message": (
                "Modern PyPSA no longer provides the legacy Pyomo LOPF backend; "
                "use the default Linopy optimizer (pyomo=false)."
            ),
        }

    network = Network(network_name)

    try:
        status, termination_condition = _optimize(
            network,
            solver_name=solver_name,
            solver_options=solver_options or {},
        )

        if status != "ok":
            return {
                "status": status,
                "termination_condition": termination_condition,
                "solver": solver_name,
                "message": (
                    "Optimization did not complete successfully: "
                    f"{termination_condition}"
                ),
            }
        
        # Get optimization results
        results = {
            "status": status,
            "termination_condition": termination_condition,
            "objective": float(network.objective),
            "solver": solver_name,
            "generators": {
                gen: {
                    "p": network.generators_t.p[gen].tolist() if len(network.snapshots) > 1 
                         else float(network.generators_t.p[gen].iloc[0]),
                    "marginal_cost": float(network.generators.loc[gen, "marginal_cost"])
                }
                for gen in network.generators.index
            },
            "loads": {
                load: network.loads_t.p[load].tolist() if len(network.snapshots) > 1
                      else float(network.loads_t.p[load].iloc[0])
                for load in network.loads.index
            },
            "buses": {
                bus: {
                    "marginal_price": network.buses_t.marginal_price[bus].tolist() 
                                     if len(network.snapshots) > 1
                                     else float(network.buses_t.marginal_price[bus].iloc[0])
                }
                for bus in network.buses.index
            }
        }
        return results
    except Exception as e:
        return {
            "status": "error",
            "message": f"Optimization failed: {str(e)}"
        }

@mcp.tool()
def optimize_investment(
    network_name: str,
    solver_name: str = "highs",
    carriers: Optional[List[str]] = None,
    multi_investment_periods: bool = False
) -> Dict[str, Any]:
    """Run investment optimization to determine optimal capacity expansion"""
    network_name = _checked_network_source(network_name, purpose="network_name")
    network = Network(network_name)
    
    try:
        # Set components as extendable if carriers specified
        if carriers:
            network.generators.loc[
                network.generators.carrier.isin(carriers), "p_nom_extendable"
            ] = True
        
        status, termination_condition = _optimize(
            network,
            solver_name=solver_name,
            multi_investment_periods=multi_investment_periods,
        )

        if status != "ok":
            return {
                "status": status,
                "termination_condition": termination_condition,
                "solver": solver_name,
                "message": (
                    "Investment optimization did not complete successfully: "
                    f"{termination_condition}"
                ),
            }
        
        # Extract investment results
        results = {
            "status": status,
            "termination_condition": termination_condition,
            "solver": solver_name,
            "objective": float(network.objective),
            "investments": {
                "generators": {
                    gen: {
                        "p_nom_opt": float(network.generators.loc[gen, "p_nom_opt"]),
                        "capital_cost": float(network.generators.loc[gen, "capital_cost"])
                    }
                    for gen in network.generators[network.generators.p_nom_extendable].index
                },
                "lines": {
                    line: {
                        "s_nom_opt": float(network.lines.loc[line, "s_nom_opt"]),
                        "capital_cost": float(network.lines.loc[line, "capital_cost"])
                    }
                    for line in network.lines[network.lines.s_nom_extendable].index
                },
                "storage_units": {
                    storage: {
                        "p_nom_opt": float(network.storage_units.loc[storage, "p_nom_opt"]),
                        "capital_cost": float(network.storage_units.loc[storage, "capital_cost"])
                    }
                    for storage in network.storage_units[network.storage_units.p_nom_extendable].index
                }
            }
        }
        return results
    except Exception as e:
        return {
            "status": "error",
            "message": f"Investment optimization failed: {str(e)}"
        }

@mcp.tool()
def import_from_csv_folder(
    folder_path: str, output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Import a CSV network and save it to NetCDF.

    ``output_path`` is explicit for new callers. Omitting it keeps the original
    API behavior and writes ``<folder name>.nc`` in the working directory. The
    resolved destination always passes through the shared path policy.
    """
    if output_path is None:
        output_path = os.path.basename(os.path.normpath(folder_path)) + ".nc"
    try:
        folder_path = checked_read_tree(folder_path, purpose="folder_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        output_path = checked_path(
            output_path, purpose="output_path", for_write=True
        )
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        network = Network()
        network.import_from_csv_folder(folder_path)
        network.export_to_netcdf(output_path)
        return {
            "status": "success",
            "message": f"Network imported from {folder_path} and saved to {output_path}",
            "network_file": output_path,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Import failed: {str(e)}"
        }

@mcp.tool()
def export_to_csv_folder(network_name: str, folder_path: str) -> Dict[str, Any]:
    """Export network to CSV files"""
    try:
        folder_path = checked_path(folder_path, purpose="folder_path", for_write=True)
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        network_name = _checked_network_source(network_name, purpose="network_name")
        network = Network(network_name)

        def write_csv_folder(staging: str) -> None:
            # powerio hands the writer a path that does not exist yet.
            os.makedirs(staging, exist_ok=True)
            network.export_to_csv_folder(staging)

        staged_directory_write(folder_path, True, write_csv_folder)
        return {
            "status": "success",
            "message": f"Network exported to {folder_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Export failed: {str(e)}"
        }


# ---------------------------------------------------------------------------
# PowerIO interchange: resolve one balanced state, use PowerIO's native PyPSA CSV
# writer, then save the PyPSA network to the NetCDF path used by other tools.
# ---------------------------------------------------------------------------

def _import_case_to_netcdf(case, output_path: str, overwrite_zero_s_nom: Optional[float]):
    """Use PowerIO's native PyPSA CSV writer, then persist the network."""
    with tempfile.TemporaryDirectory(prefix="powermcp-pypsa-") as staging_root:
        staging = os.path.join(staging_root, "case")
        written = case.emit("pypsa-csv", staging)
        network = Network()
        network.import_from_csv_folder(staging)
    warnings = list(diagnostic_messages(written.diagnostics))

    # PyPSA regulates bus voltage through Bus.v_mag_pu_set; transfer the
    # generator targets retained by the PowerIO CSV writer before solving.
    if "v_mag_pu_set" in network.generators:
        generators = network.generators
        regulated = generators.loc[
            generators["control"].isin(("PV", "Slack"))
            & generators["v_mag_pu_set"].notna()
            & generators["bus"].isin(network.buses.index),
            ["bus", "v_mag_pu_set"],
        ].sort_index(kind="stable")
        for bus, targets in regulated.groupby("bus", sort=True):
            values = targets["v_mag_pu_set"].astype(float)
            target = float(values.iloc[0])
            network.buses.loc[bus, "v_mag_pu_set"] = target
            if not np.allclose(values.to_numpy(), target):
                warnings.append(
                    f"multiple voltage targets regulate bus {bus}; "
                    f"using {target} from the first generator"
                )

    # Generator rows retain source order. Map supported transition costs
    # into the PyPSA generator table.
    source_generators = list(case.network.generators)
    if len(source_generators) == len(network.generators):
        network.generators["start_up_cost"] = [
            float((generator.get("cost") or {}).get("startup", 0.0))
            for generator in source_generators
        ]
        network.generators["shut_down_cost"] = [
            float((generator.get("cost") or {}).get("shutdown", 0.0))
            for generator in source_generators
        ]
    else:
        warnings.append(
            "generator transition costs could not be restored because the "
            "PowerIO and PyPSA generator counts differ"
        )
    constant_costs = sum(
        1
        for generator in source_generators
        if (generator.get("cost") or {}).get("model") == 2
        and (generator.get("cost") or {}).get("coeffs")
        and float((generator.get("cost") or {})["coeffs"][-1]) != 0.0
    )
    if constant_costs:
        warnings.append(
            f"{constant_costs} generator constant polynomial cost term(s) "
            "have no equivalent in the PyPSA generator objective and were dropped"
        )

    zero_ratings = 0
    for table in (network.lines, network.transformers):
        if "s_nom" not in table:
            continue
        zero = table["s_nom"] == 0
        zero_ratings += int(zero.sum())
        if overwrite_zero_s_nom is not None:
            table.loc[zero, "s_nom"] = overwrite_zero_s_nom
    if zero_ratings and overwrite_zero_s_nom is None:
        warnings.append(
            f"{zero_ratings} branch(es) with rating 0 imported with s_nom 0; "
            "pass overwrite_zero_s_nom to set a value"
        )
    try:
        network.export_to_netcdf(output_path)
    except OSError as exc:
        raise OSError(f"failed to write network to {output_path}: {exc}") from exc
    info = {
        "buses": len(network.buses),
        "generators": len(network.generators),
        "loads": len(network.loads),
        "lines": len(network.lines),
        "transformers": len(network.transformers),
        "shunt_impedances": len(network.shunt_impedances),
    }
    return info, warnings, written


@mcp.tool()
def import_case_from_any(
    file_path: str,
    output_path: str,
    source_format: Optional[str] = None,
    overwrite_zero_s_nom: Optional[float] = None,
    operating_point: Optional[int] = None,
    study_commit: Optional[int] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    edits: str = "",
    to_balanced: bool = False,
    base_mva: float = 100.0,
) -> Dict[str, Any]:
    """Import any powerio readable case file as a PyPSA network saved to a
    NetCDF file.

    Reads any balanced PowerIO format or a ``.pio.json`` module and writes a
    PyPSA network to output_path. Select a TimeSeries with time_index and a ScenarioSet with scenario_id.
    The selected typed value is validated before conversion.
    PowerIO's native PyPSA writer preserves supported costs and element status.

    Args:
        file_path: Path to the case file
        output_path: Where to save the imported network (.nc)
        source_format: Input format name (matpower, powermodels-json,
            egret-json, psse, powerworld); inferred from the file extension
            when omitted
        overwrite_zero_s_nom: Replacement s_nom for branches with rating 0
        operating_point: Compatibility alias for time_index
        study_commit: Retired package selector; export a Tellegen Study state as IR
        time_index: Explicit TimeSeries index
        scenario_id: Explicit ScenarioSet identifier
        edits: JSON list of typed what-if edits PowerIO applies before the
            conversion, in list order, for example
            [{"op": "set_load_active_power", "load": "loads:0", "mw": 91.5}]
            Consecutive updates of one class apply as one atomic batch, and a
            bus load reallocation sees the values the edits before it produced.
        to_balanced: Authorize the multiconductor to balanced transformation;
            the response carries its readiness report as `lowering`
        base_mva: System base for that transformation

    Returns:
        Dict with status, the saved network_file path, component counts, and
        warnings about dropped or adjusted data
    """
    try:
        file_path = checked_path(file_path, purpose="file_path")
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        output_path = checked_path(output_path, purpose="output_path", for_write=True)
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        prepared = resolve_solver_case(
            file_path=file_path,
            source_format=source_format,
            operating_point=operating_point,
            study_commit=study_commit,
            time_index=time_index,
            scenario_id=scenario_id,
            edits=edits,
            to_balanced=to_balanced,
            base_mva=base_mva,
        )
        info, notes, written = _import_case_to_netcdf(
            prepared, output_path, overwrite_zero_s_nom
        )
        fields = prepared.response_fields(written)
        fields["warnings"] = list(dict.fromkeys([*fields["warnings"], *notes]))
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to import case: {str(e)}"}
    return {
        "status": "success",
        "message": f"Network imported and saved to {output_path}",
        "network_file": output_path,
        "info": info,
        **fields,
    }


@mcp.tool()
def import_case_from_json(
    network_json: str = "",
    output_path: str = "",
    overwrite_zero_s_nom: Optional[float] = None,
    operating_point: Optional[int] = None,
    study_commit: Optional[int] = None,
    time_index: Optional[int] = None,
    scenario_id: Optional[str] = None,
    powerio_ir: str = "",
    edits: str = "",
    to_balanced: bool = False,
    base_mva: float = 100.0,
) -> Dict[str, Any]:
    """Import PowerIO model JSON or one selected ``.pio.json`` module state
    as a PyPSA network saved to a NetCDF file.

    Accepts the `json` string returned by the powerio server's parse tool,
    or a durable package emitted by its package tools. A package containing
    stored state data requires exactly one operating-point or study-commit selector. A
    case parsed once there loads here without passing a file around or
    re-parsing it. Model JSON expects source-valued tables (MW, degrees)
    as parse emits them, not the per-unit normalize form. Writes the
    network to output_path (use a .nc extension); pass that path as
    network_name to the other tools. powerio is a core dependency, so this is
    always available.

    Args:
        network_json: The JSON transport string from powerio
        output_path: Where to save the imported network (.nc)
        overwrite_zero_s_nom: Replacement s_nom for branches with rating 0
        operating_point: Compatibility alias for time_index
        study_commit: Retired package selector; export a Tellegen Study state as IR
        time_index: Explicit TimeSeries index
        scenario_id: Explicit ScenarioSet identifier
        powerio_ir: Serialized PowerIO IR from the powerio server (the
            preferred spelling; network_json is its alias)
        edits: JSON list of typed what-if edits PowerIO applies before the
            conversion, in list order, for example
            [{"op": "set_load_active_power", "load": "loads:0", "mw": 91.5}]
            Consecutive updates of one class apply as one atomic batch, and a
            bus load reallocation sees the values the edits before it produced.
        to_balanced: Authorize the multiconductor to balanced transformation;
            the response carries its readiness report as `lowering`
        base_mva: System base for that transformation

    Returns:
        Dict with status, the saved network_file path, component counts, and
        warnings about dropped or adjusted data
    """
    if not output_path:
        return {"status": "error", "message": "output_path is required"}
    try:
        output_path = checked_path(output_path, purpose="output_path", for_write=True)
    except PathNotAllowed as exc:
        return {"status": "error", "message": str(exc)}
    try:
        prepared = resolve_solver_case(
            network_json=network_json,
            operating_point=operating_point,
            study_commit=study_commit,
            time_index=time_index,
            scenario_id=scenario_id,
            powerio_ir=powerio_ir,
            edits=edits,
            to_balanced=to_balanced,
            base_mva=base_mva,
        )
        info, notes, written = _import_case_to_netcdf(
            prepared, output_path, overwrite_zero_s_nom
        )
        fields = prepared.response_fields(written)
        fields["warnings"] = list(dict.fromkeys([*fields["warnings"], *notes]))
    except Exception as e:
        return {"status": "error", "message": f"Failed to import case: {str(e)}"}
    return {
        "status": "success",
        "message": f"Network imported and saved to {output_path}",
        "network_file": output_path,
        "info": info,
        **fields,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
