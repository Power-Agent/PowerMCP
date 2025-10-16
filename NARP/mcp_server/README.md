Minimal local MCP server skeleton for reliability-assessment.

Usage:

from mcp_server.manager import JobManager
jm = JobManager()
job_id = jm.submit_simulation('reliabilityassessment/integration_test')
status = jm.get_job_status(job_id)
# wait for completion then
result = jm.get_job_result(job_id)

Notes:
- jobs stored in sqlite at mcp_jobs.sqlite
- job working dirs under ./mcp_jobs
- parse_output is minimal and should be extended for production
