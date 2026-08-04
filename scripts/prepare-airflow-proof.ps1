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

if (-not (Test-Path -LiteralPath (Join-Path $AirflowPath "airflow.yaml"))) {
    astro dev init --from-template learning-airflow
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
Write-Output "  astro dev start --standalone"
Write-Output "  astro dev bash"
Write-Output "  airflow users create --help"
Write-Output "  airflow dags unpause retail_orders_daily"
Write-Output "  airflow dags trigger -r airflow-run-20260723T040000Z retail_orders_daily"
Write-Output "Use a temporary read-only Airflow credential; do not commit or record it."

if (-not $SkipStart) {
    astro dev start --standalone
}
