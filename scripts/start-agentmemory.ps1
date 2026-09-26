$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $PSScriptRoot
$dataDirectory = Join-Path $workspace ".agentmemory-data"
$healthUrl = "http://localhost:3111/agentmemory/health"
$logDirectory = Join-Path $workspace "logs"

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

try {
    $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
    if ($health.StatusCode -eq 200) {
        Write-Output "Agentmemory is already healthy at http://localhost:3111"
        exit 0
    }
} catch {
    # A partial engine-only startup is repaired below.
}

$env:CI = "1"
$env:AGENTMEMORY_USE_DOCKER = "1"
$env:GRAPH_EXTRACTION_ENABLED = "true"
$env:AGENTMEMORY_AUTO_COMPRESS = "true"
$env:AGENTMEMORY_SUPPRESS_COST_WARNING = "1"

cmd.exe /d /c "npx.cmd -y @agentmemory/agentmemory@latest stop --force >nul 2>nul"

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "`$env:CI='1'; `$env:AGENTMEMORY_USE_DOCKER='1'; `$env:GRAPH_EXTRACTION_ENABLED='true'; `$env:AGENTMEMORY_AUTO_COMPRESS='true'; `$env:AGENTMEMORY_SUPPRESS_COST_WARNING='1'; npx -y @agentmemory/agentmemory@latest --data-dir '$dataDirectory' --tools core"
)

Start-Process -FilePath "powershell.exe" `
    -ArgumentList $arguments `
    -WorkingDirectory $workspace `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDirectory "agentmemory.out.log") `
    -RedirectStandardError (Join-Path $logDirectory "agentmemory.err.log")

$deadline = (Get-Date).AddSeconds(60)
do {
    try {
        $health = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
        if ($health.StatusCode -eq 200) {
            Write-Output "Agentmemory is healthy at http://localhost:3111"
            exit 0
        }
    } catch {
        # Keep waiting while the service and its local engine initialize.
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

Write-Error "Agentmemory did not become healthy within 60 seconds. Check logs under $logDirectory"
exit 1