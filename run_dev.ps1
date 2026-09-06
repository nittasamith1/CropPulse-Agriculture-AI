# CropPulse Development Launcher for Windows PowerShell
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Starting CropPulse - AI Agriculture Intelligence Stack" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Virtual environment .venv not found." -ForegroundColor Red
    exit 1
}

# 1. Start Backend in separate window
Write-Host "[1/2] Launching FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { .\.venv\Scripts\Activate.ps1; uvicorn backend.main:app --reload --port 8000 }"

# 2. Start Frontend in separate window
Write-Host "[2/2] Launching Frontend Server on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { python -m http.server 3000 --directory frontend }"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Services are starting!" -ForegroundColor Green
Write-Host "  * Web Application:  http://localhost:3000" -ForegroundColor Yellow
Write-Host "  * Interactive Docs: http://localhost:8000/api/docs" -ForegroundColor Yellow
Write-Host "  * Health Check:     http://localhost:8000/api/health" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
