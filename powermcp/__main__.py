"""Enable ``python -m powermcp`` to run the CLI.

The generated MCP client configs launch servers via
``<python> -m powermcp run <tool>`` (an absolute interpreter is more robust than
the bare ``powermcp`` console script for GUI hosts that don't inherit the shell
PATH). Executing a package with ``-m`` runs this module, which delegates to the
same entry point as the ``powermcp`` console script.
"""

from .cli import main

if __name__ == "__main__":
    main()
