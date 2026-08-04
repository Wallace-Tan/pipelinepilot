param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$IncidentId = "inc-retail-orders-20260723"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command cortex -ErrorAction SilentlyContinue)) {
    throw "cortex is not on PATH. Install and authenticate the Snowflake CoCo CLI first."
}

$operator = @{ "X-Actor-Id" = "demo-operator"; "X-Actor-Role" = "operator" }
$admin = @{ "X-Actor-Id" = "demo-admin"; "X-Actor-Role" = "admin" }

Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/demo/reset" -Headers $admin | Out-Null
$result = Invoke-RestMethod -Method Post -Uri "$BaseUrl/v1/incidents/$IncidentId/investigate" -Headers $operator

if ($result.adapter_mode -ne "live") {
    throw "PipelinePilot did not produce a live recommendation. adapter_mode=$($result.adapter_mode); fallback_reason=$($result.fallback_reason)"
}
if ($null -ne $result.fallback_reason) {
    throw "PipelinePilot reported a fallback reason during the live verification."
}
if (@($result.evidence).Count -eq 0 -or (@($result.evidence | Where-Object { $_.mode -ne "live" }).Count -gt 0)) {
    throw "At least one investigation evidence record was not marked live."
}

$requiredSources = @("monitoring", "airflow_log", "dbt", "snowflake_metadata")
$actualSources = @($result.evidence | ForEach-Object { $_.source })
foreach ($source in $requiredSources) {
    if ($actualSources -notcontains $source) { throw "Missing live evidence source: $source" }
}

$status = Invoke-RestMethod -Method Get -Uri "$BaseUrl/v1/demo/status" -Headers $operator
[pscustomobject]@{
    incident_id = $result.incident.id
    adapter_mode = $result.adapter_mode
    evidence_modes = @($result.evidence | ForEach-Object { $_.mode } | Sort-Object -Unique)
    evidence_sources = $actualSources | Sort-Object -Unique
    decision_status = $status.adapter_status.decision.status
    recovery_boundary = "fixture-only"
} | ConvertTo-Json -Depth 5
