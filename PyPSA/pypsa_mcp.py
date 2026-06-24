import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from pypsa import Network
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any


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


# ============= Network Information =============

@mcp.tool()
def get_network_info(network_name: str) -> Dict[str, Any]:
    """Get basic information about the network"""
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
    if snapshots:
        snapshots = pd.DatetimeIndex(snapshots)
    network = Network(name=name, snapshots=snapshots, crs=crs)
    network.export_to_netcdf(f"{name}.nc")
    return {
        "status": "success",
        "message": f"Network '{name}' created and saved to {name}.nc"
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
    """Run a linear optimal power flow (LOPF) on the network"""
    network = Network(network_name)
    
    try:
        status = network.lopf(
                    solver_name=solver_name,
                    pyomo=pyomo,
                    solver_options=solver_options or {}
                )
        
        # Get optimization results
        results = {
            "status": status,
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
    network = Network(network_name)
    
    try:
        # Set components as extendable if carriers specified
        if carriers:
            network.generators.loc[
                network.generators.carrier.isin(carriers), "p_nom_extendable"
            ] = True
        
        status = network.lopf(
                    solver_name=solver_name
                )
        
        # Extract investment results
        results = {
            "status": status,
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
def import_from_csv_folder(folder_path: str) -> Dict[str, Any]:
    """Import network from CSV files"""
    try:
        network = Network()
        network.import_from_csv_folder(folder_path)
        network_name = os.path.basename(folder_path) + ".nc"
        network.export_to_netcdf(network_name)
        return {
            "status": "success",
            "message": f"Network imported from {folder_path} and saved to {network_name}"
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
        network = Network(network_name)
        network.export_to_csv_folder(folder_path)
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
# powerio bridge: import any powerio readable case as a PyPSA network.
# powerio parses MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels
# JSON, and egret JSON; the case becomes a PYPOWER ppc dict, pypsa imports it,
# and the network is saved to a .nc file whose path the other tools accept as
# network_name. powerio is an optional extra, so the tools degrade to a status
# dict when it is missing.
# ---------------------------------------------------------------------------

_POWERIO_HINT = "powerio not installed: pip install 'powerio[mcp,matrix]'"

# powerio bus kind -> MATPOWER/PYPOWER BUS_TYPE code
# NOTE: _PPC_BUS_TYPE and _powerio_case_to_ppc are duplicated between
# pandapower/panda_mcp.py and PyPSA/pypsa_mcp.py (server scripts are
# standalone); keep the two copies identical and sync any fix to both.
_PPC_BUS_TYPE = {"PQ": 1.0, "PV": 2.0, "REF": 3.0, "ISOLATED": 4.0}


def _powerio_case_to_ppc(case) -> Dict[str, Any]:
    """Build a PYPOWER ppc dict from a powerio Network.

    Values are MATPOWER style (MW, MVAr, degrees), which is what powerio's
    parsed source tables carry; in-service loads and shunts are summed into
    the bus table the way MATPOWER stores them.
    """
    import numpy as np

    buses = case.buses
    row_of = {b["id"]: i for i, b in enumerate(buses)}
    bus = np.zeros((len(buses), 13))
    for i, b in enumerate(buses):
        bus[i, :] = (
            b["id"], _PPC_BUS_TYPE.get(b["kind"], 1.0), 0.0, 0.0, 0.0, 0.0,
            b["area"], b["vm"], b["va"], b["base_kv"], b["zone"], b["vmax"], b["vmin"],
        )
    for load in case.loads:
        i = row_of.get(load["bus"])
        if i is not None and load["in_service"]:
            bus[i, 2] += load["p"]
            bus[i, 3] += load["q"]
    for shunt in case.shunts:
        i = row_of.get(shunt["bus"])
        if i is not None and shunt["in_service"]:
            bus[i, 4] += shunt["g"]
            bus[i, 5] += shunt["b"]

    gens = case.generators
    gen = np.zeros((len(gens), 21))
    for i, g in enumerate(gens):
        gen[i, :10] = (
            g["bus"], g["pg"], g["qg"], g["qmax"], g["qmin"], g["vg"],
            g["mbase"], float(g["in_service"]), g["pmax"], g["pmin"],
        )

    branches = case.branches
    branch = np.zeros((len(branches), 13))
    for i, br in enumerate(branches):
        branch[i, :] = (
            br["from_id"], br["to_id"], br["r"], br["x"], br["b"],
            br["rate_a"], br["rate_b"], br["rate_c"], br["tap"], br["shift"],
            float(br["in_service"]), br["angmin"], br["angmax"],
        )

    ppc = {
        "version": "2",
        "baseMVA": float(case.base_mva),
        "bus": bus,
        "gen": gen,
        "branch": branch,
    }

    # gencost rows are [model, startup, shutdown, ncost, coeffs...] with
    # coefficients left-aligned after ncost, padded to the widest row — the
    # layout from_ppc reads. MATPOWER requires cost data for all gens or none,
    # so a partial cost set is dropped rather than padded with fake rows.
    costs = [g["cost"] for g in gens]
    if costs and all(c is not None for c in costs):
        gencost = np.zeros((len(costs), 4 + max(len(c["coeffs"]) for c in costs)))
        for i, c in enumerate(costs):
            gencost[i, :4] = (c["model"], c["startup"], c["shutdown"], c["ncost"])
            gencost[i, 4:4 + len(c["coeffs"])] = c["coeffs"]
        ppc["gencost"] = gencost
    return ppc


def _import_case_to_netcdf(case, output_path: str, overwrite_zero_s_nom: Optional[float]):
    """Import a powerio case into a fresh PyPSA network, save it to
    output_path, and collect warnings about anything the ppc import cannot
    represent."""
    ppc = _powerio_case_to_ppc(case)
    warnings = []
    isolated = ppc["bus"][:, 1] == 4.0
    if isolated.any():
        # import_from_pypower_ppc indexes ["", "PQ", "PV", "Slack"] by bus
        # type, so type 4 would raise; PyPSA has no isolated bus type.
        ppc["bus"][isolated, 1] = 1.0
        warnings.append(f"{int(isolated.sum())} isolated bus(es) imported as PQ")
    if any(g["cost"] is not None for g in case.generators):
        warnings.append(
            "generator cost data is not representable by the PyPSA ppc import and was dropped"
        )
    if (ppc["bus"][:, 9] == 0).any():
        warnings.append("buses with base_kv 0 are assigned v_nom 1 by PyPSA")

    # PyPSA's import_from_pypower_ppc ignores the ppc status columns (branch
    # col 10, gen col 7), so out-of-service elements would import as fully
    # active and silently change topology. Drop them before import and report
    # the count. (pandapower's from_ppc honors status, so its bridge does not
    # need this — keep that asymmetry in mind when syncing the shared helper.)
    br_oos = ppc["branch"][:, 10] == 0.0
    if br_oos.any():
        ppc["branch"] = ppc["branch"][~br_oos]
        warnings.append(
            f"{int(br_oos.sum())} out-of-service branch(es) dropped "
            "(PyPSA's ppc import does not model branch status)"
        )
    gen_oos = ppc["gen"][:, 7] == 0.0
    if gen_oos.any():
        ppc["gen"] = ppc["gen"][~gen_oos]
        if "gencost" in ppc:
            ppc["gencost"] = ppc["gencost"][~gen_oos]
        warnings.append(
            f"{int(gen_oos.sum())} out-of-service generator(s) dropped "
            "(PyPSA's ppc import does not model generator status)"
        )

    # Only in-service branches remain now, so the rating-0 check is exact.
    if overwrite_zero_s_nom is None and (ppc["branch"][:, 5] == 0).any():
        warnings.append(
            "branches with rating 0 imported with s_nom 0; pass overwrite_zero_s_nom to set a value"
        )
    network = Network()
    network.import_from_pypower_ppc(ppc, overwrite_zero_s_nom=overwrite_zero_s_nom)
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
    return info, warnings


@mcp.tool()
def import_case_from_any(
    file_path: str,
    output_path: str,
    source_format: Optional[str] = None,
    overwrite_zero_s_nom: Optional[float] = None,
) -> Dict[str, Any]:
    """Import any powerio readable case file as a PyPSA network saved to a
    NetCDF file.

    Reads MATPOWER .m, PSS/E .raw (v33), PowerWorld .aux, PowerModels JSON, or
    egret JSON via powerio and writes a PyPSA network to output_path (use a
    .nc extension); pass that path as network_name to the other tools. PyPSA's
    ppc import drops generator cost data; anything else it cannot represent is
    listed in the returned warnings. Branches with rating 0 are imported with
    s_nom 0 unless overwrite_zero_s_nom supplies a value. powerio is a core
    dependency, so this is always available.

    Args:
        file_path: Path to the case file
        output_path: Where to save the imported network (.nc)
        source_format: Input format name (matpower, powermodels-json,
            egret-json, psse, powerworld); inferred from the file extension
            when omitted
        overwrite_zero_s_nom: Replacement s_nom for branches with rating 0

    Returns:
        Dict with status, the saved network_file path, component counts, and
        warnings about dropped or adjusted data
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.parse_file(file_path, source_format)
        info, warnings = _import_case_to_netcdf(case, output_path, overwrite_zero_s_nom)
    except FileNotFoundError:
        return {"status": "error", "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to import case: {str(e)}"}
    return {
        "status": "success",
        "message": f"Network imported and saved to {output_path}",
        "network_file": output_path,
        "info": info,
        "warnings": warnings,
    }


@mcp.tool()
def import_case_from_json(
    network_json: str,
    output_path: str,
    overwrite_zero_s_nom: Optional[float] = None,
) -> Dict[str, Any]:
    """Import a powerio JSON transport string as a PyPSA network saved to a
    NetCDF file.

    Accepts the `json` string returned by the powerio server's parse tool,
    so a case parsed once there loads here without passing a file around or
    re-parsing it. Expects source-valued tables (MW, degrees)
    as parse emits them, not the per-unit normalize form. Writes the
    network to output_path (use a .nc extension); pass that path as
    network_name to the other tools. powerio is a core dependency, so this is
    always available.

    Args:
        network_json: The JSON transport string from powerio
        output_path: Where to save the imported network (.nc)
        overwrite_zero_s_nom: Replacement s_nom for branches with rating 0

    Returns:
        Dict with status, the saved network_file path, component counts, and
        warnings about dropped or adjusted data
    """
    try:
        import powerio
    except ImportError:
        return {"status": "error", "message": _POWERIO_HINT}
    try:
        case = powerio.from_json(network_json)
        info, warnings = _import_case_to_netcdf(case, output_path, overwrite_zero_s_nom)
    except Exception as e:
        return {"status": "error", "message": f"Failed to import case: {str(e)}"}
    return {
        "status": "success",
        "message": f"Network imported and saved to {output_path}",
        "network_file": output_path,
        "info": info,
        "warnings": warnings,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
