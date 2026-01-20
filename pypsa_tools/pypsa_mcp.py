import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from pypsa import Network
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any
import json
from common.utils import PowerError, power_mcp_tool

# Create an MCP server
mcp = FastMCP("PyPSA-MCP")

# ============= Network Information =============

@power_mcp_tool(mcp)
def get_network_info(network_name: str) -> str:
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
    return json.dumps(info, indent=2)

@power_mcp_tool(mcp)
def get_component_details(
    network_name: str,
    component_type: str,
    component_id: Optional[str] = None
) -> str:
    """Get detailed information about a specific component or all components of a type"""
    network = Network(network_name)
    
    if not hasattr(network, component_type):
        return json.dumps({
            "status": "error",
            "message": f"Component type '{component_type}' not found"
        })
    
    component_df = getattr(network, component_type)
    
    if component_id:
        if component_id not in component_df.index:
            return json.dumps({
                "status": "error",
                "message": f"Component '{component_id}' not found in {component_type}"
            })
        result = component_df.loc[component_id].to_dict()
    else:
        result = component_df.to_dict('index')
    
    return json.dumps(result, indent=2, default=str)

# ============= Network Construction =============

@power_mcp_tool(mcp)
def create_network(
    name: str = "network",
    snapshots: Optional[List[str]] = None,
    crs: str = "EPSG:4326"
) -> str:
    """Create a new PyPSA network"""
    if snapshots:
        snapshots = pd.DatetimeIndex(snapshots)
    network = Network(name=name, snapshots=snapshots, crs=crs)
    network.export_to_netcdf(f"{name}.nc")
    return json.dumps({
        "status": "success",
        "message": f"Network '{name}' created and saved to {name}.nc"
    })

@power_mcp_tool(mcp)
def add_bus(
    network_name: str,
    bus_id: str,
    v_nom: float = 380.0,
    x: Optional[float] = None,
    y: Optional[float] = None,
    carrier: str = "AC"
) -> str:
    """Add a bus to the network"""
    network = Network(network_name)
    network.add("Bus", bus_id, v_nom=v_nom, x=x, y=y, carrier=carrier)
    network.export_to_netcdf(network_name)
    return json.dumps({
        "status": "success",
        "message": f"Bus '{bus_id}' added to network"
    })

@power_mcp_tool(mcp)
def add_generator(
    network_name: str,
    gen_id: str,
    bus: str,
    p_nom: float,
    marginal_cost: float = 0.0,
    carrier: str = "generator",
    p_min_pu: float = 0.0,
    p_max_pu: float = 1.0
) -> str:
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
    return json.dumps({
        "status": "success",
        "message": f"Generator '{gen_id}' added to network"
    })

@power_mcp_tool(mcp)
def add_load(
    network_name: str,
    load_id: str,
    bus: str,
    p_set: float
) -> str:
    """Add a load to the network"""
    network = Network(network_name)
    network.add("Load", load_id, bus=bus, p_set=p_set)
    network.export_to_netcdf(network_name)
    return json.dumps({
        "status": "success",
        "message": f"Load '{load_id}' added to network"
    })

@power_mcp_tool(mcp)
def add_line(
    network_name: str,
    line_id: str,
    bus0: str,
    bus1: str,
    x: float,
    r: float = 0.0,
    s_nom: float = 1000.0,
    length: float = 1.0
) -> str:
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
    return json.dumps({
        "status": "success",
        "message": f"Line '{line_id}' added to network"
    })

@power_mcp_tool(mcp)
def add_storage_unit(
    network_name: str,
    storage_id: str,
    bus: str,
    p_nom: float,
    max_hours: float = 6.0,
    efficiency_store: float = 0.9,
    efficiency_dispatch: float = 0.9,
    cyclic_state_of_charge: bool = True
) -> str:
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
    return json.dumps({
        "status": "success",
        "message": f"Storage unit '{storage_id}' added to network"
    })

# ============= Optimization =============

@power_mcp_tool(mcp)
def optimize_network(
    network_name: str,
    solver_name: str = "highs",
    formulation: str = "kirchhoff",
    pyomo: bool = False,
    solver_options: Optional[Dict] = None
) -> str:
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
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Optimization failed: {str(e)}"
        })

@power_mcp_tool(mcp)
def optimize_investment(
    network_name: str,
    solver_name: str = "highs",
    carriers: Optional[List[str]] = None,
    multi_investment_periods: bool = False
) -> str:
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
        return json.dumps(results, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Investment optimization failed: {str(e)}"
        })

@power_mcp_tool(mcp)
def import_from_csv_folder(folder_path: str) -> str:
    """Import network from CSV files"""
    try:
        network = Network()
        network.import_from_csv_folder(folder_path)
        network_name = os.path.basename(folder_path) + ".nc"
        network.export_to_netcdf(network_name)
        return json.dumps({
            "status": "success",
            "message": f"Network imported from {folder_path} and saved to {network_name}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Import failed: {str(e)}"
        })

@power_mcp_tool(mcp)
def export_to_csv_folder(network_name: str, folder_path: str) -> str:
    """Export network to CSV files"""
    try:
        network = Network(network_name)
        network.export_to_csv_folder(folder_path)
        return json.dumps({
            "status": "success",
            "message": f"Network exported to {folder_path}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Export failed: {str(e)}"
        })


if __name__ == "__main__":
    mcp.run(transport="stdio")