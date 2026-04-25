$ErrorActionPreference = "Stop"

$pidFile = Join-Path $PSScriptRoot "dashboard-pids.json"

if (-not (Test-Path $pidFile)) {
  Write-Output "No dashboard PID file found."
  exit 0
}

$payload = Get-Content $pidFile | ConvertFrom-Json
$ids = @($payload.backend_pid, $payload.frontend_pid) | Where-Object { $_ }

foreach ($id in $ids) {
  try {
    Stop-Process -Id $id -Force -ErrorAction Stop
    Write-Output "Stopped PID $id"
  } catch {
    Write-Output "PID $id is not running"
  }
}

Remove-Item $pidFile -ErrorAction SilentlyContinue
