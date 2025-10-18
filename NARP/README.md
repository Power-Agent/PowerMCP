# reliability-assessment
Reliability Assessment Module

The goal of this project is to port an original Fortran-based power system reliability assessment program (“NARP”) to Python. The program calculates reliability indices such as LOLE (Loss of Load Expectation), HLOLE (Hourly LOLE), and EUE (Expected Unserved Energy) for transmission systems. The Python implementation closely matches the original FORTRAN behaviour when benchmarked via RMSE metrics.

## PowerMCP Integration

Within the PowerMCP repository the MCP entry point is exposed via `NARP/narp_mcp.py`.  
You can launch the server with `python -m NARP.narp_mcp`, which registers tools like `submit_simulation`, `get_job_summary`, and `validate_input` – matching the pattern used by other integrations (e.g. pandapower).  
This integration builds on the open-source Python port maintained at [zylpascal/NARP](https://github.com/zylpascal/NARP).

## Using NARP with PowerMCP

### Start the server

```bash
python -m NARP.narp_mcp
```

Run this command from the PowerMCP repository root. The server copies each submitted test directory into `NARP/mcp_jobs/`, executes `narpMain.py`, and tracks job metadata so you can retrieve logs and summaries later.

### Example prompts for MCP clients

Use any MCP-aware assistant to issue natural-language instructions. A few examples:

- “List the available tools and give me a short description of each.”
- “Use the reliability analysis tool with the input directory C:/cases/narp_case1, run the simulation, and send me the summary of the results afterward.”
- “Please validate the NARP inputs located at `C:/cases/narp_case1` before running the reliability study.”
- “Submit a NARP reliability job for `C:/cases/narp_case1`, keep checking until it finishes, then send me the TABLE 12/13 summary.”
- “Cancel the current NARP reliability run with job id `job_abcd1234` and confirm the status change.”

Adjust directory paths to match your environment. After completion you can inspect `output_python.txt` and `run.log` inside the corresponding folder under `NARP/mcp_jobs/`.

## Additional resources

For full algorithmic documentation, data formats, and advanced usage, refer to the upstream project at [zylpascal/NARP](https://github.com/zylpascal/NARP).

## Contacts

- Shan Yang – yangsh237@mail2.sysu.edu.cn
- Yongli Zhu – yzhu16@alum.utk.edu
