---
name: pipelinepilot-incident
description: Investigate a failed data pipeline with sanitized evidence and produce a cited, structured recommendation for PipelinePilot.
tools:
  - snowflake_object_search
  - snowflake_sql_execute
---

# When to Use

Use this skill when PipelinePilot asks CoCo to inspect an Airflow run, Airflow logs, dbt health, or Snowflake metadata for a failed pipeline incident.

# Safety Contract

- Read-only investigation only. Never trigger, retry, pause, unpause, mutate, or delete Airflow or Snowflake resources.
- Never return credentials, tokens, email addresses, card numbers, or raw personal identifiers.
- Use the incident ID, pipeline name, and run ID supplied by the caller; do not broaden the search to unrelated customer data.
- Return only the JSON shape requested by the caller. Do not wrap it in Markdown or explanatory prose.
- Cite only evidence or runbook IDs supplied by the caller.

# Investigation Guidance

For Airflow context, inspect DAG run state, task state, and the relevant task log. For Snowflake context, use metadata-only queries to compare the named source and staging objects. Prefer summaries and bounded metadata over raw logs or unbounded query results.

For decision support, distinguish observed facts from hypotheses, select a confidence band rather than a precise probability, and propose a controlled action without executing it. PipelinePilot’s backend policy and approval services remain the authority for recovery.
