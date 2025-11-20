# Auto-activate uv virtual environment for this project
# Usage: .\activate.ps1 or source activate.ps1

$venv_path = Join-Path $PSScriptRoot ".venv"
$activate_script = Join-Path $venv_path "Scripts\Activate.ps1"

if (Test-Path $activate_script) {
    & $activate_script
    Write-Host "Virtual environment activated!" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found at: $venv_path" -ForegroundColor Yellow
    Write-Host "Run 'uv sync' to create the virtual environment." -ForegroundColor Yellow
}

