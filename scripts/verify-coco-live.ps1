param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$IncidentId = "inc-retail-orders-20260723",
    [string]$Connection = "QE45776",
    [string]$ExpectedAccount = "bl63744.ap-southeast-5.aws"
)

$ErrorActionPreference = "Stop"

$configuredCommand = [Environment]::GetEnvironmentVariable("PIPELINEPILOT_COCO_COMMAND")
if ([string]::IsNullOrWhiteSpace($configuredCommand)) {
    $configuredCommand = "cortex"
}
$cortex = Get-Command $configuredCommand -ErrorAction SilentlyContinue
if (-not $cortex -and $configuredCommand -eq "cortex") {
    $cortex = Get-Command cortex.cmd -ErrorAction SilentlyContinue
}
if (-not $cortex) {
    throw "CoCo CLI '$configuredCommand' is not on PATH. Install and authenticate the Snowflake CoCo CLI first."
}
$cortexCommand = $cortex.Source

$configuredConnection = [Environment]::GetEnvironmentVariable("PIPELINEPILOT_COCO_CONNECTION")
if (-not [string]::IsNullOrWhiteSpace($configuredConnection) -and $configuredConnection -ne $Connection) {
    throw "PIPELINEPILOT_COCO_CONNECTION is '$configuredConnection', expected '$Connection'."
}

function Invoke-CocoCommand {
    param([string[]]$Arguments)

    $output = & $cortexCommand @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "CoCo command failed: $($Arguments -join ' ')"
    }
    return ($output -join [Environment]::NewLine)
}

$connectionList = Invoke-CocoCommand @("connections", "list")
try {
    $connectionDocument = $connectionList | ConvertFrom-Json
} catch {
    throw "CoCo returned an invalid connection list."
}
$connectionProperty = $connectionDocument.connections.PSObject.Properties[$Connection]
if (-not $connectionProperty) {
    throw "CoCo connection '$Connection' is not configured."
}
$actualAccount = [string]$connectionProperty.Value.account
if ($actualAccount -ne $ExpectedAccount) {
    throw "CoCo connection '$Connection' resolves to '$actualAccount', expected '$ExpectedAccount'."
}
$expectedAccountIdentifier = ($actualAccount -split '\.')[0]
Write-Host "CoCo connection verified: $Connection -> $actualAccount"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not on PATH. CoCo requires uv for Airflow integration commands."
}

try {
    Invoke-CocoCommand @("airflow", "health") | Out-Null
} catch {
    throw "CoCo Airflow health preflight failed. Confirm the read-only Airflow integration and uv are available."
}

$metadataPrompt = "Using only read-only session metadata, return one JSON object with the Snowflake account identifier, authenticated user, active role, warehouse, database, and schema. Do not query business tables, expose secrets, or perform any write or administrative operation."
try {
    $metadataOutput = Invoke-CocoCommand @("--connection", $Connection, "--sql-read-only", "--allowed-tools", "SQL", "--print", $metadataPrompt, "--output-format", "stream-json")
} catch {
    throw "Read-only CoCo metadata preflight failed or timed out for connection '$Connection'."
}
if ([string]::IsNullOrWhiteSpace($metadataOutput)) {
    throw "Read-only CoCo metadata preflight returned no output."
}
if ($metadataOutput -notmatch [regex]::Escape($expectedAccountIdentifier) -or $metadataOutput -notmatch '\\?"account(?:_identifier)?\\?"\s*:') {
    throw "Read-only CoCo metadata preflight did not return the expected Snowflake account metadata."
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
foreach ($adapter in @("monitoring", "log_investigation", "dbt_health", "snowflake_metadata")) {
    $adapterStatus = $status.adapter_status.$adapter
    if ($adapterStatus.mode -ne "live" -or $adapterStatus.source -ne "coco") {
        throw "Adapter '$adapter' was not verified as live CoCo context."
    }
}
if ($status.adapter_status.decision.mode -ne "live" -or $status.adapter_status.decision.source -ne "coco") {
    throw "Decision adapter was not verified as live CoCo output."
}
[pscustomobject]@{
    incident_id = $result.incident.id
    connection = $Connection
    snowflake_account = $actualAccount
    adapter_mode = $result.adapter_mode
    evidence_modes = @($result.evidence | ForEach-Object { $_.mode } | Sort-Object -Unique)
    evidence_sources = $actualSources | Sort-Object -Unique
    decision_status = $status.adapter_status.decision.status
    recovery_boundary = "fixture-only"
} | ConvertTo-Json -Depth 5
