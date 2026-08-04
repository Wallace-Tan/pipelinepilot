$ErrorActionPreference = "Stop"
$baseUrl = if ($env:PIPELINEPILOT_BASE_URL) { $env:PIPELINEPILOT_BASE_URL } else { "http://127.0.0.1:8000" }
$headers = @{ "X-Actor-Id" = "demo-operator"; "X-Actor-Role" = "operator" }
$adminHeaders = @{ "X-Actor-Id" = "demo-admin"; "X-Actor-Role" = "admin" }
$incidentId = "inc-retail-orders-20260723"
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

function Invoke-DemoRequest($Method, $Path, $Headers, $Body = $null) {
    try {
        $params = @{ Method = $Method; Uri = "$baseUrl$Path"; Headers = $Headers; ErrorAction = "Stop" }
        if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10); $params.ContentType = "application/json" }
        return Invoke-RestMethod @params
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { "unknown" }
        throw "Demo request failed: $Method $Path ($status). $($_.Exception.Message)"
    }
}

function Assert-ExpectedFailure($Method, $Path, $Headers, $ExpectedStatus, $ExpectedCode, $Body = $null) {
    try {
        $params = @{ Method = $Method; Uri = "$baseUrl$Path"; Headers = $Headers; ErrorAction = "Stop" }
        if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10); $params.ContentType = "application/json" }
        Invoke-RestMethod @params | Out-Null
        throw "Expected $ExpectedCode ($ExpectedStatus) from $Method $Path, but the request succeeded."
    } catch {
        if ($_.Exception.Message.StartsWith("Expected $ExpectedCode")) { throw }
        $response = $_.Exception.Response
        if ($null -eq $response) { throw "Expected $ExpectedCode ($ExpectedStatus) from $Method $Path, but no response was available." }
        $actualStatus = [int]$response.StatusCode
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        $payload = $reader.ReadToEnd() | ConvertFrom-Json
        if ($actualStatus -ne $ExpectedStatus -or $payload.error.code -ne $ExpectedCode) {
            throw "Expected $ExpectedCode ($ExpectedStatus) from $Method $Path, received $($payload.error.code) ($actualStatus)."
        }
    }
}

Invoke-DemoRequest POST "/v1/demo/reset" $adminHeaders | Out-Null
Invoke-DemoRequest GET "/v1/demo/status" $headers | Out-Null
Invoke-DemoRequest GET "/v1/incidents" $headers | Out-Null
Invoke-DemoRequest POST "/v1/incidents/$incidentId/investigate" $headers | Out-Null
Assert-ExpectedFailure POST "/v1/incidents/$incidentId/investigate" @{ "X-Actor-Id" = "demo-viewer"; "X-Actor-Role" = "viewer" } 403 "forbidden_role"
Assert-ExpectedFailure POST "/v1/incidents/$incidentId/validate" $headers 404 "not_found"
$missingApprovalKey = "demo-replay-missing-approval"
Assert-ExpectedFailure POST "/v1/incidents/$incidentId/executions" (@{} + $headers + @{ "Idempotency-Key" = $missingApprovalKey }) 409 "approval_required" (@{ action = "schema_drift_recovery" })
$key = "demo-replay-schema-drift"
$request = @{ action = "schema_drift_recovery" }
$actionHeaders = @{} + $headers + @{ "Idempotency-Key" = $key }
Invoke-DemoRequest POST "/v1/incidents/$incidentId/approvals" $actionHeaders $request | Out-Null
Invoke-DemoRequest POST "/v1/incidents/$incidentId/executions" $actionHeaders $request | Out-Null
Invoke-DemoRequest POST "/v1/incidents/$incidentId/validate" $headers | Out-Null
$report = Invoke-DemoRequest GET "/v1/incidents/$incidentId/report" $headers
$stopwatch.Stop()

[pscustomobject]@{
    incident_id = $report.incident.id
    final_status = $report.incident.status
    feedback_count = $report.feedback_count
    elapsed_seconds = [math]::Round($stopwatch.Elapsed.TotalSeconds, 2)
    mode = $report.incident.mode
} | ConvertTo-Json
