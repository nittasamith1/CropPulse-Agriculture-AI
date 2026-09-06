@echo off
TITLE CropPulse Development Launcher
echo ========================================================
echo   Starting CropPulse - AI Agriculture Intelligence Stack
echo ========================================================
echo.

:: Check if virtualenv exists
IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment .venv not found.
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "CropPulse - Backend API (Port 8000)" cmd /k ".venv\Scripts\activate && uvicorn backend.main:app --reload --port 8000"

echo [2/2] Launching Static Frontend on http://localhost:3000 ...
start "CropPulse - Frontend (Port 3000)" cmd /k "python -m http.server 3000 --directory frontend"

echo.
echo ========================================================
echo   Services are running!
echo   * Web Application:  http://localhost:3000
echo   * Interactive Docs: http://localhost:8000/api/docs
echo   * Health Endpoint:  http://localhost:8000/api/health
echo ========================================================
echo Press any key to close this launcher window (services remain active).
pause >nul
