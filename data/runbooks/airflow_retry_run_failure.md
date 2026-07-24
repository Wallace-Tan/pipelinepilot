# Airflow Retry and Run Failure

Document ID: `runbook-airflow-retry`

## Triage

Confirm DAG, task, run ID, retry count, and current state from monitoring. Use sanitized logs for signatures and avoid exposing raw task output.

## Retry Criteria

Retry is allowed only when the failure is transient, idempotent, and policy permits the actor. High-risk or ambiguous failures require approval.

## Recovery

Bind any retry or clear-task action to a policy decision, approval record when required, and idempotency key.
