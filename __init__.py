"""
PowerMCP - Power System Analysis MCP Server Collection

An open-source collection of MCP (Model Context Protocol) servers 
for power system simulation and analysis software.

Supported tools:
- pandapower: Power system modeling and analysis
- PyPSA: Power system optimization
- ANDES: Power system dynamics simulation
- OpenDSS: Distribution system analysis
- And more...
"""

__version__ = "0.1.0"

# Import availability flags and key functions from submodules
from pandapower_tools import (
    PANDAPOWER_AVAILABLE,
    create_empty_network as pandapower_create_empty_network,
    create_test_network as pandapower_create_test_network,
    load_network as pandapower_load_network,
    run_power_flow as pandapower_run_power_flow,
    run_dc_power_flow as pandapower_run_dc_power_flow,
    get_network_info as pandapower_get_network_info,
    add_bus as pandapower_add_bus,
    add_line as pandapower_add_line,
    add_load as pandapower_add_load,
    add_generator as pandapower_add_generator,
    add_ext_grid as pandapower_add_ext_grid,
    run_contingency_analysis as pandapower_run_contingency_analysis,
    get_available_std_types as pandapower_get_available_std_types,
)

from pypsa_tools import (
    PYPSA_AVAILABLE,
    create_network as pypsa_create_network,
    get_network_info as pypsa_get_network_info,
    add_bus as pypsa_add_bus,
    add_generator as pypsa_add_generator,
    add_load as pypsa_add_load,
    add_line as pypsa_add_line,
    run_power_flow as pypsa_run_power_flow,
    run_optimal_power_flow as pypsa_run_optimal_power_flow,
    load_network as pypsa_load_network,
    save_network as pypsa_save_network,
)

# Convenience imports for submodules
from . import pandapower_tools
from . import pypsa_tools

__all__ = [
    '__version__',
    # Pandapower
    'PANDAPOWER_AVAILABLE',
    'pandapower_create_empty_network',
    'pandapower_create_test_network',
    'pandapower_load_network',
    'pandapower_run_power_flow',
    'pandapower_run_dc_power_flow',
    'pandapower_get_network_info',
    'pandapower_add_bus',
    'pandapower_add_line',
    'pandapower_add_load',
    'pandapower_add_generator',
    'pandapower_add_ext_grid',
    'pandapower_run_contingency_analysis',
    'pandapower_get_available_std_types',
    # PyPSA
    'PYPSA_AVAILABLE',
    'pypsa_create_network',
    'pypsa_get_network_info',
    'pypsa_add_bus',
    'pypsa_add_generator',
    'pypsa_add_load',
    'pypsa_add_line',
    'pypsa_run_power_flow',
    'pypsa_run_optimal_power_flow',
    'pypsa_load_network',
    'pypsa_save_network',
    # Submodules
    'pandapower_tools',
    'pypsa_tools',
]
