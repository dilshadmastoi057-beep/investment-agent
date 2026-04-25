$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendPython = Join-Path $root "venv\Scripts\python.exe"
$frontendDir = Join-Path $root "frontend\web"
$pidFile = Join-Path $PSScriptRoot "dashboard-pids.json"

if (-not (Test-Path $backendPython)) {
  throw "Backend Python not found at $backendPython"
}

if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
  throw "Frontend package.json not found at $frontendDir"
}

$backend = Start-Process -FilePath $backendPython `
  -ArgumentList "-m", "uvicorn", "backend.api.main:app", "--host", "127.0.0.1", "--port", "8002" `
  -WorkingDirectory $root `
  -PassThru

$frontend = Start-Process -FilePath "npm.cmd" `
  -ArgumentList "start" `
  -WorkingDirectory $frontendDir `
  -PassThru

$payload = @{
  backend_pid = $backend.Id
  frontend_pid = $frontend.Id
  backend_url = "http://127.0.0.1:8002"
  frontend_url = "http://127.0.0.1:3000"
  started_at = (Get-Date).ToString("o")
}

$payload | ConvertTo-Json | Set-Content -Path $pidFile -Encoding UTF8

Write-Output "Backend PID: $($backend.Id)"
Write-Output "Frontend PID: $($frontend.Id)"
Write-Output "Backend URL: http://127.0.0.1:8002"
Write-Output "Frontend URL: http://127.0.0.1:3000"
