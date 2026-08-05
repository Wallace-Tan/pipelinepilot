# Live Airflow and Cortex verification

This is the execution record template for PP-009 and PP-011. Live investigation context may come from Cortex, but PipelinePilot policy, approval, recovery, validation, and SQLite audit/report behavior remain server-side and fixture-only.

## Preconditions

- Use a non-production Snowflake account and a dedicated read-only role; never use `ACCOUNTADMIN`.
- Install and authenticate the Snowflake CoCo CLI (`cortex`); `cortex connections` is the source of truth for the configured Snowflake profiles.
- Configure CoCo Airflow access with temporary local credentials; use a FAB-enabled or remote Airflow instance for a true least-privilege read-only role.
- Do not commit `connections.toml`, tokens, passwords, Airflow databases, raw logs, or recordings containing secrets.

Official references: [Cortex CLI reference](https://docs.snowflake.com/en/user-guide/cortex-code/cli-reference), [Cortex Airflow integration](https://docs.snowflake.com/en/user-guide/cortex-code/airflow), and [Astro local CLI quickstart](https://www.astronomer.io/docs/astro/cli/get-started-cli).

## Local Airflow proof

Run this from the repository root. It creates exactly one Astro project at `C:\tmp\pipelinepilot-airflow` and does not add Airflow files to Git. The helper detects `.astro\config.yaml` and refuses to initialize a non-empty non-Astro directory, preventing nested `learning-airflow` project folders:

```powershell
.\scripts\prepare-airflow-proof.ps1
```

From PowerShell, manually unpause and trigger the seeded run:

```powershell
Set-Location C:\tmp\pipelinepilot-airflow
astro dev run dags unpause retail_orders_daily
astro dev run dags trigger -r airflow-run-20260723T040000Z retail_orders_daily
```

The generated Airflow 3 local runtime uses `SimpleAuthManager` and does not expose the `airflow users` CLI or Viewer roles. Use only the temporary local credentials printed by `astro dev start` for these read-only CoCo calls; this local proof is not a production least-privilege authentication setup. Use a FAB-enabled or remote Airflow instance when a true read-only Airflow role is required.

The failed task must be `transform_orders`, and its sanitized error must identify `ColumnNotFound: order_channel`.

Configure the temporary PowerShell session:

```powershell
$env:AIRFLOW_API_URL = "http://127.0.0.1:8080"
$env:AIRFLOW_USERNAME = "<local-airflow-user>"
$env:AIRFLOW_PASSWORD = "<local-airflow-password>"
```

Verify read-only CoCo commands:

```powershell
cortex airflow health
cortex airflow dags list
cortex airflow dags get retail_orders_daily
cortex airflow runs list retail_orders_daily
cortex airflow tasks list retail_orders_daily airflow-run-20260723T040000Z
```

## Snowflake proof

```powershell
cortex.cmd connections list
cortex.cmd --connection QE45776 --sql-read-only --allowed-tools SQL --print "Using only read-only session metadata, return one JSON object with the Snowflake account identifier, authenticated user, active role, warehouse, database, and schema. Do not query business tables, expose secrets, or perform any write or administrative operation." --output-format stream-json
```

Confirm that `QE45776` resolves to the intended non-production account and read-only role. The active profile may be different; do not rely on it. Use only a metadata prompt and confirm that no write or administrative operation is attempted.

## PipelinePilot proof

On native Windows, the installer may expose `cortex.cmd` rather than an extensionless `cortex` command. In the same PowerShell window used to start the backend, configure the installed wrapper explicitly:

```powershell
$cortexBin = Join-Path $env:LOCALAPPDATA "cortex\bin"
$env:Path = "$cortexBin;$env:Path"
Get-Command cortex.cmd
cortex.cmd --version
$env:PIPELINEPILOT_COCO_COMMAND = "cortex.cmd"
```

Start the backend with:

```powershell
$env:PIPELINEPILOT_COCO_ENABLED = "true"
$env:PIPELINEPILOT_COCO_COMMAND = "cortex.cmd"
$env:PIPELINEPILOT_COCO_CONNECTION = "QE45776"
$env:PIPELINEPILOT_COCO_TIMEOUT_SECONDS = "90"
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then run:

```powershell
.\scripts\verify-coco-live.ps1
```

PipelinePilot adds `--sql-read-only --allowed-tools SQL` to every CoCo invocation. The script first verifies that `QE45776` resolves to the expected Snowflake account, that `uv` is available for CoCo Airflow commands, that CoCo Airflow health succeeds, and that a read-only metadata prompt completes with the expected account identifier. It then fails closed unless the investigation response contains live evidence from monitoring, Airflow logs, dbt context, and Snowflake metadata, plus a live validated recommendation. A CLI login alone is not evidence of PipelinePilot integration.

## Governance proof

After live investigation, repeat the normal lifecycle and confirm:

- Execution without approval returns `approval_required`.
- Approved recovery returns `fixture://recovery/...`.
- Validation succeeds only after recovery.
- Audit and report records are present.

## Fallback proof

Restart the backend with:

```powershell
$env:PIPELINEPILOT_COCO_COMMAND = "cortex-command-not-installed"
```

Investigation must still complete with fixture evidence, a safe fallback reason, deterministic citations, and the same policy/approval/recovery boundaries. Existing automated tests cover unavailable CoCo and malformed/uncited decision output.

## Evidence record

Record the date, CLI versions, sanitized command results, PipelinePilot investigation response, UI status, fallback response, approval denial, fixture recovery reference, validation, audit, and report. Do not record credentials, connection files, raw sensitive logs, or SQLite files.

## Current verification state

As of 5 August 2026, `cortex.cmd --version` reports `Cortex Code v1.1.53`, and the configured profiles include `QE45776`. Live verification is complete only when the preconditions above are completed and `scripts/verify-coco-live.ps1` succeeds; otherwise use the clearly labeled deterministic fallback path.
