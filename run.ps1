$ErrorActionPreference = "Stop"

Write-Host "Starting DECHO App..." -ForegroundColor Green

$currentDir = Get-Location

# 1. Start Backend
Write-Host "Starting Backend Server (Port 8000)..." -ForegroundColor Cyan
# Check if uv is installed, otherwise use python
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    $backendCmd = "uv run uvicorn server.main:app --reload --port 8000"
} else {
    $backendCmd = "python -m uvicorn server.main:app --reload --port 8000"
}
Start-Process powershell -WorkingDirectory $currentDir -ArgumentList "-NoExit", "-Command", "$backendCmd"

# 2. Start Frontend
Write-Host "Starting Frontend Web App (Port 3000)..." -ForegroundColor Cyan
$webDir = Join-Path $currentDir "web"
if (Test-Path $webDir) {
    # Check if node_modules exists, if not, run npm install
    if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
        Start-Process powershell -WorkingDirectory $webDir -ArgumentList "-NoExit", "-Command", "npm install; npm run dev"
    } else {
        Start-Process powershell -WorkingDirectory $webDir -ArgumentList "-NoExit", "-Command", "npm run dev"
    }
} else {
    Write-Error "Web directory not found at $webDir"
}

Write-Host "------------------------------------------------" -ForegroundColor Green
Write-Host "Backend running at: http://localhost:8000"
Write-Host "Frontend running at: http://localhost:3000"
Write-Host "------------------------------------------------" -ForegroundColor Green
