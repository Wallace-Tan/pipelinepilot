# Live Airflow and Cortex verification

This is the execution record template for PP-009 and PP-011. Live investigation context may come from Cortex, but PipelinePilot policy, approval, recovery, validation, and SQLite audit/report behavior remain server-side and fixture-only.

## Preconditions

- Use a non-production Snowflake account and a dedicated read-only role; never use `ACCOUNTADMIN`.
- Install and authenticate the Snowflake CoCo CLI (`cortex`) and Snowflake CLI (`snow`).
- Configure CoCo Airflow access with temporary read-only credentials.
- Do not commit `connections.toml`, tokens, passwords, Airflow databases, raw logs, or recordings containing secrets.

Official references: [Cortex CLI reference](https://docs.snowflake.com/en/user-guide/cortex-code/cli-reference), [Cortex Airflow integration](https://docs.snowflake.com/en/user-guide/cortex-code/airflow), and [Astro local CLI quickstart](https://www.astronomer.io/docs/astro/cli/get-started-cli).

## Local Airflow proof

Run this from the repository root. It creates the proof project under `C:\tmp` and does not add Airflow files to Git:

```powershell
.\scripts\prepare-airflow-proof.ps1
```

In the Airflow shell, create the lowest available read-only user, then manually unpause and trigger the seeded run:

```bash
airflow users create --help
airflow dags unpause retail_orders_daily
airflow dags trigger -r airflow-run-20260723T040000Z retail_orders_daily
```

The failed task must be `transform_orders`, and its sanitized error must identify `ColumnNotFound: order_channel`.

Configure the temporary PowerShell session:

```powershell
$env:AIRFLOW_API_URL = "http://127.0.0.1:8080"
$env:AIRFLOW_USERNAME = "pipelinepilot_reader"
$env:AIRFLOW_PASSWORD = "<temporary-password>"
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
snow connection test -c pipelinepilot_ro
cortex -c pipelinepilot_ro
```

Use only a metadata prompt. Confirm that the intended demo objects are visible and that no write or administrative operation is attempted.

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
$env:PIPELINEPILOT_COCO_CONNECTION = "pipelinepilot_ro"
$env:PIPELINEPILOT_COCO_TIMEOUT_SECONDS = "90"
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then run:

```powershell
.\scripts\verify-coco-live.ps1
```

The script fails closed unless the investigation response contains live evidence from monitoring, Airflow logs, dbt context, and Snowflake metadata, plus a live validated recommendation. A CLI login alone is not evidence of PipelinePilot integration.

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

As of 5 August 2026, `cortex.cmd --version` reports `Cortex Code v1.1.53`. The local environment does not have Airflow or Snowflake CLI available and has no configured read-only Airflow URL or CoCo connection, so live verification is pending. Submit the deterministic fixture path unless the preconditions above are completed and `scripts/verify-coco-live.ps1` succeeds.
