# Pandapower MCP Python Integration

## Requirements

- [pandapower](https://github.com/e2nIEE/pandapower)
- Python 3.10 or higher

## Available Tools

- **Create an empty network**: Initialize a new, empty Pandapower network.
- **Load a network**: Load a network from a `.json` or `.p` file.
- **Run power flow**: Perform power flow analysis (Newton-Raphson or Backward/Forward Sweep).
- **Contingency analysis**: Run N-1 or N-2 contingency analysis on lines and transformers.
- **Get network info**: Retrieve statistics and data for buses, lines, transformers, generators, loads, and switches.
- **Users can add more features based on pandapower API**


## Prompt Example

- Could you perform an N-1 contingency analysis using Pandapower on the case file `test_case.json`? Based on the results, please provide suggestions for enhancing the system's security.


## Resources
- [Pandapower Documentation](https://pandapower.readthedocs.io/)