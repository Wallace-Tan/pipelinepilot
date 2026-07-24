# Schema Drift Response

Document ID: `runbook-schema-drift`

## Triage

Confirm the failing pipeline, failed model or task, and whether the issue is limited to fixture, sandbox, or live mode. Collect monitoring status, sanitized task logs, dbt context, and read-only warehouse metadata.

## Compare source metadata with staging projections

Compare observed source columns with the staging model projection. Treat missing required columns, changed types, and removed fields as schema drift until proven otherwise.

## Validate downstream model contracts

Review downstream model contracts, tests, and freshness. Do not retry a failed transformation until the proposed recovery has a policy decision and any required approval.

## Recovery

In fixture mode, update the staging projection, rerun the affected model chain, and validate freshness before reporting recovery.
