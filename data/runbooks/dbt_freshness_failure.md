# dbt Freshness Failure

Document ID: `runbook-dbt-freshness`

## Triage

Identify the stale source, the last successful load timestamp, and affected downstream models. Use sanitized artifacts only.

## Decision Points

If freshness is stale because the upstream loader failed, investigate the loader before running dbt. If freshness is stale after a successful load, validate model dependencies and warehouse availability.

## Recovery

Run only the minimum affected model selection after policy review. Record validation evidence before closing the incident.
