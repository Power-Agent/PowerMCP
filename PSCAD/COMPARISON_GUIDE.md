# Automation Comparison: Traditional vs. MCP

## 1. Traditional scripting

A script should start a simulation using a non-blocking operation before polling its status. Do not call `Project.run()` and then expect the polling loop to run: `Project.run()` blocks for the build-and-run operation, so the code cannot poll until that call returns.

A simplified lifecycle using the non-blocking PSCAD project API is:

```python
import time
import mhi.pscad

pscad = mhi.pscad.launch()
project = pscad.load(r"C:\temp\vdiv.pscx")
project.parameters(R1="100 [ohm]")

# Start the build/run without blocking on the whole simulation.
project.start()

saw_running = False
while True:
    status, progress = project.run_status()
    if status == "Run":
        saw_running = True
        print(f"Simulation progress: {progress}%")
    elif status == "Build":
        print("Building project...")
    else:
        # Idle can mean completed, not started, or failed. It is not
        # sufficient on its own to prove a successful simulation.
        break
    time.sleep(1)

if not saw_running:
    print("The project never reported running; inspect build messages/output.")
print(project.output())
```

This is an illustrative lifecycle, not a substitute for checking the installed PSCAD API version and the project's build/run messages. In particular, a return to idle is not, by itself, proof that the build and simulation succeeded.

## 2. MCP workflow

The PowerMCP server exposes the lifecycle as separate tools so an agent can start work, poll progress, and inspect diagnostics without holding a single call open for the full simulation.

For a typical run:

1. **Optional compile preflight — `build_project`**: compile the project without starting a simulation. The tool returns `built`, `errors`, and `warnings`. This is a blocking compile operation; its watchdog is disabled, so it can occupy the PSCAD worker until the build finishes.
2. **Start — `run_project`**: starts the build-and-run using PSCAD's non-blocking `Project.start()` and returns promptly. It first checks that PSCAD is licensed.
3. **Poll — `get_run_status`**: call periodically. Its high-level `state` is `building`, `running`, or `idle_or_finished`; progress is reported while running.
4. **Diagnose — `get_build_messages`**: if the project returns to idle without ever reporting `running`, inspect build errors and warnings. Also inspect project output/results when needed. The idle state alone does not distinguish successful completion from a run that never started or failed.

Do not infer that a simulation was cancelled just because a client-side wait timed out. A timeout means the caller did not obtain completion within its wait; it does not establish that PSCAD stopped the operation.

## 3. Watchdogs and long-running simulations

The executor's watchdog is not a mechanism for making a blocking `project.run()` pattern safe. A blocking call that exceeds its watchdog can time out while occupying the single PSCAD worker, preventing other PSCAD commands from being serviced. Long simulations should use the non-blocking start-and-poll workflow instead.

The `build_project` tool is intentionally different: it performs a blocking compile preflight with its watchdog disabled. Treat it as a potentially long-running operation and do not assume other PSCAD commands can run concurrently while it is building.

## Summary of value

| Feature | Traditional scripting | PowerMCP |
| :--- | :--- | :--- |
| **Orchestration** | The script manages start, polling, and diagnostics | Separate tools expose start, status, and build diagnostics |
| **Progress** | The script polls PSCAD and decides what to report | `get_run_status` returns a high-level state and progress |
| **Failure diagnosis** | The script must inspect messages and output | `get_build_messages` provides structured errors and warnings |
| **Long operations** | The script must manage waits and recovery | Non-blocking `run_project` avoids waiting for the full run inside the start call |
| **Success detection** | Must distinguish completion from idle/failure | The agent must still inspect the observed lifecycle and diagnostics; idle alone is ambiguous |

The server reduces orchestration work, but it does not make every idle status a successful run or make a timed-out blocking operation safe.
