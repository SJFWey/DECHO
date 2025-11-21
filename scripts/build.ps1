# DECHO Build Script for Windows
# This script automates the complete build process for the DECHO Windows application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DECHO Windows Application Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = $PSScriptRoot | Split-Path -Parent
$WEB_DIR = Join-Path $PROJECT_ROOT "web"
$TAURI_BINARIES = Join-Path $WEB_DIR "src-tauri\binaries"

# Check for cargo and add to PATH if missing
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    $CargoPath = Join-Path $env:USERPROFILE ".cargo\bin"
    if (Test-Path $CargoPath) {
        Write-Host "Adding Cargo to PATH: $CargoPath" -ForegroundColor Cyan
        $env:Path += ";$CargoPath"
    } else {
        Write-Warning "Cargo not found in PATH and not found at $CargoPath. Rust build may fail."
    }
}

# Change to project root
Set-Location $PROJECT_ROOT

# Step 1: Build Python Backend with PyInstaller
Write-Host "[1/4] Building Python backend executable..." -ForegroundColor Yellow
try {
    # Check for virtual environment python
    $VenvPython = Join-Path $PROJECT_ROOT ".venv\Scripts\python.exe"
    
    if (Test-Path $VenvPython) {
        Write-Host "Using virtual environment: $VenvPython" -ForegroundColor Cyan
        & $VenvPython -m PyInstaller decho-server.spec --clean
    } else {
        Write-Host "Virtual environment not found, falling back to global pyinstaller" -ForegroundColor Yellow
        pyinstaller decho-server.spec --clean
    }

    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed"
    }
    Write-Host "✓ Backend built successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend build failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Copy backend executable to Tauri binaries
Write-Host "[2/4] Copying backend executable to Tauri..." -ForegroundColor Yellow
try {
    $BackendExe = Join-Path $PROJECT_ROOT "dist\decho-server.exe"
    $TargetExe = Join-Path $TAURI_BINARIES "decho-server-x86_64-pc-windows-msvc.exe"
    
    if (!(Test-Path $BackendExe)) {
        throw "Backend executable not found at $BackendExe"
    }
    
    # Ensure binaries directory exists
    New-Item -ItemType Directory -Force -Path $TAURI_BINARIES | Out-Null
    
    Copy-Item $BackendExe $TargetExe -Force
    Write-Host "✓ Backend copied to Tauri binaries" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to copy backend: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Build Next.js frontend
Write-Host "[3/4] Building Next.js frontend..." -ForegroundColor Yellow
try {
    Set-Location $WEB_DIR
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed"
    }
    Write-Host "✓ Frontend built successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Frontend build failed: $_" -ForegroundColor Red
    Set-Location $PROJECT_ROOT
    exit 1
}

# Step 4: Build Tauri application
Write-Host "[4/4] Building Tauri application..." -ForegroundColor Yellow
try {
    npm run tauri build
    if ($LASTEXITCODE -ne 0) {
        throw "Tauri build failed"
    }
    Write-Host "✓ Tauri application built successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Tauri build failed: $_" -ForegroundColor Red
    Set-Location $PROJECT_ROOT
    exit 1
}

Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Build completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installer location:" -ForegroundColor Yellow
Write-Host "  $WEB_DIR\src-tauri\target\release\bundle\" -ForegroundColor White
Write-Host ""
