# PyPSA MCP Power System Analysis Server

A comprehensive Model Context Protocol (MCP) server for PyPSA (Python for Power System Analysis), providing tools for power system modeling, optimization, and analysis.

## Requirements

- [PyPSA](https://pypsa.org/) >= 0.25.0
- Python 3.10 or higher
- MCP and FastMCP packages
- At least one LP solver supported by PyPSA:
  - **Open Source**: HiGHS (recommended), CBC, GLPK
  - **Commercial**: Gurobi (Acadenic License available)
- Optional dependencies:
  - `cartopy` for geographic plotting
  - `networkx` for network analysis

### Functionalities

- [x] `get_network_info` - Get basic network statistics (buses, generators, loads, etc.)
- [x] `get_component_details` - Get detailed information about specific components
- [x] `create_network` - Create a new PyPSA network with snapshots
- [x] `add_bus` - Add electrical buses to the network
- [x] `add_generator` - Add power generators with technical parameters
- [x] `add_load` - Add electrical loads to buses
- [x] `add_line` - Add transmission lines between buses
- [x] `add_storage_unit` - Add battery storage or pumped hydro storage
- [x] `import_from_csv_folder` - Import network from CSV files
- [x] `export_to_csv_folder` - Export network to CSV format

# Future functionalities
- [ ] `calculate_statistics` - Calculate capacity factors, line loading, and curtailment
- [ ] `calculate_emissions` - Calculate CO2 emissions based on generator dispatch
- [ ] `add_transformer` - Add transformers between voltage levels
- [ ] `add_link` - Add controllable links (HVDC, P2G, etc.)
- [ ] `add_store` - Add energy stores (hydrogen, heat, etc.)
- [ ] `add_emission_limit` - Add CO2 emission constraints
- [ ] `remove_component` - Remove components from network
- [ ] `modify_component` - Update component parameters
- [ ] `run_contingency_analysis` - N-1 contingency analysis
- [ ] `calculate_ptdf` - Power Transfer Distribution Factors
- [ ] `calculate_lodf` - Line Outage Distribution Factors
- [ ] `run_power_flow` - Run AC or DC power flow calculations
- [ ] `check_network_consistency` - Validate network connectivity
- [ ] `sensitivity_analysis` - Parameter sensitivity studies
- [ ] `monte_carlo_analysis` - Uncertainty analysis
- [ ] `set_snapshots` - Define time periods with weights
- [ ] `add_time_series` - Add time-varying data (wind, solar, demand)
- [ ] `resample_time_series` - Change temporal resolution
- [ ] `slice_time_series` - Extract time periods
- [ ] `add_constraint` - Add custom linear constraints
- [ ] `remove_constraint` - Remove constraints
- [ ] `multi_horizon_optimization` - Rolling horizon optimization
- [ ] `security_constrained_opf` - SCOPF with contingencies
- [ ] `add_heat_sector` - Add heating demand and supply
- [ ] `add_transport_sector` - Add EV and transport demand
- [ ] `add_hydrogen_network` - Add P2G and hydrogen infrastructure
- [ ] `optimize_sector_coupling` - Integrated multi-sector optimization
- [ ] `plot_network` - Generate network topology plots
- [ ] `plot_dispatch` - Visualize generation dispatch
- [ ] `generate_report` - Create comprehensive analysis reports
- [ ] `export_results_to_excel` - Export results in Excel format
- [ ] `merge_networks` - Combine multiple networks
- [ ] `simplify_network` - Network reduction preserving key properties
- [ ] `aggregate_buses` - Combine buses with strategies
- [ ] `run_myopic_optimization` - Myopic investment planning
- [ ] `run_perfect_foresight` - Perfect foresight optimization
- [ ] `stochastic_optimization` - Stochastic scenario optimization
- [ ] `robust_optimization` - Robust optimization under uncertainty
- [ ] `optimize_network` - Run Linear Optimal Power Flow (LOPF)
- [ ] `optimize_investment` - Run capacity expansion optimization


## Testing

Run the test suite:
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_pypsa_mcp.py

# Run with coverage
pytest --cov=pypsa_mcp tests/
```

## Useful Resources

- [PyPSA Documentation](https://pypsa.readthedocs.io/)
- [PyPSA Examples](https://github.com/PyPSA/PyPSA/tree/master/examples)
- [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) - European power system model
- [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) - Global power system models
- [MCP Documentation](https://modelcontextprotocol.io/)