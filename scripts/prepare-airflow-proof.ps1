param(
    [string]$AirflowPath = "C:\tmp\pipelinepilot-airflow",
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command astro -ErrorAction SilentlyContinue)) {
    throw "Astro CLI is not installed. Install it from the official Astro CLI guide, then rerun this script."
}

New-Item -ItemType Directory -Force -Path $AirflowPath | Out-Null
Set-Location -LiteralPath $AirflowPath

$projectMarker = Join-Path $AirflowPath ".astro\config.yaml"
if (-not (Test-Path -LiteralPath $projectMarker)) {
    $existingEntries = @(Get-ChildItem -Force -LiteralPath $AirflowPath)
    if ($existingEntries.Count -gt 0) {
        throw "AirflowPath '$AirflowPath' is not an Astro project and is not empty. Clean the temporary proof directory or choose an empty path."
    }

    astro dev init --force --name "pipelinepilot-airflow"
}

if (-not (Test-Path -LiteralPath $projectMarker)) {
    throw "Astro initialization did not create '$projectMarker'."
}

$dagPath = Join-Path $AirflowPath "dags\retail_orders_daily.py"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dagPath) | Out-Null
@'
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from pendulum import datetime


def fail_schema_drift() -> None:
    raise AirflowException("ColumnNotFound: order_channel")


with DAG(
    dag_id="retail_orders_daily",
    start_date=datetime(2026, 7, 23, tz="UTC"),
    schedule=None,
    catchup=False,
) as dag:
    transform_orders = PythonOperator(
        task_id="transform_orders",
        python_callable=fail_schema_drift,
    )
'@ | Set-Content -LiteralPath $dagPath -Encoding utf8

astro dev parse

Write-Output "Airflow proof DAG prepared at $dagPath"
Write-Output "Next manual steps, performed outside CoCo:"
Write-Output "  astro dev run dags unpause retail_orders_daily"
Write-Output "  astro dev run dags trigger -r airflow-run-20260723T040000Z retail_orders_daily"
Write-Output "Use only the temporary local credentials printed by astro dev start; Airflow 3 SimpleAuth does not provide a Viewer user CLI. Do not commit credentials."

if (-not $SkipStart) {
    astro dev start --no-browser
}
