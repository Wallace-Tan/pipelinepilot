param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. Install the documented prerequisite, then rerun this verifier."
    }
}

Require-Command "uv"
Require-Command "node"
Require-Command "npm.cmd"

Push-Location (Join-Path $repoRoot "backend")
try {
    if (-not $SkipInstall) { uv sync }
    uv run pytest
} finally {
    Pop-Location
}

Push-Location (Join-Path $repoRoot "frontend")
try {
    if (-not $SkipInstall) { npm.cmd install }
    npm.cmd run build
} finally {
    Pop-Location
}

$trackedSensitive = @(git -C $repoRoot ls-files | Where-Object {
    $_ -match '(^|/)(\.env($|\.)|.*\.sqlite3($|-)|.*\.log$|connections\.toml$)' -or
    $_ -match '(^|/)(credentials|secrets)(/|$)'
})
if ($trackedSensitive.Count -gt 0) {
    throw "Sensitive or generated files are tracked: $($trackedSensitive -join ', ')"
}

[pscustomobject]@{
    status = "ready"
    backend_tests = "passed"
    frontend_build = "passed"
    tracked_sensitive_files = 0
} | ConvertTo-Json
