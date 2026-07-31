$ErrorActionPreference = "Stop"
$databasePath = Join-Path $PSScriptRoot "..\backend\pipelinepilot.sqlite3"
if (Test-Path -LiteralPath $databasePath) {
    Remove-Item -LiteralPath $databasePath
    Write-Output "Removed fixture database: $databasePath"
} else {
    Write-Output "Fixture database was already clean."
}
Write-Output "Start the backend to recreate migrations and the seeded schema-drift incident."
