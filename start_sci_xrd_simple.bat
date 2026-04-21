@echo off
chcp 65001 >nul
title Sci-XRD System Launcher v2.0.0
color 0A

echo.
echo ========================================================
echo           Sci-XRD Intelligent Analysis System
echo ========================================================
echo Version: 2.0.0 - Simple Launcher
echo Function: One-click startup for complete analysis system
echo ========================================================
echo.

REM Switch to current directory
cd /d "%~dp0"

REM Check Python
echo [1/4] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found, please install Python 3.8+
    echo.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo OK: Python environment is ready

REM Check dependencies
echo [2/4] Checking system dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing necessary dependencies...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Dependency installation failed
        echo Please install manually: pip install fastapi uvicorn[standard]
        pause
        exit /b 1
    )
    echo OK: Dependencies installed
) else (
    echo OK: Dependencies already installed
)

REM Start system
echo [3/4] Starting Web service...
echo.
echo ========================================================
echo           Web Service Starting...
echo ========================================================
echo Opening browser...
echo.
echo If browser doesn't open automatically, please visit:
echo   http://localhost:8000
echo.
echo Main Features:
echo   - Single file XRD analysis
echo   - Batch file processing
echo   - AI intelligent recommendations
echo   - Professional chart generation
echo   - Multiple format export
echo ========================================================
echo.

REM Open browser
start "" "http://localhost:8000"

REM Start Web service
echo [4/4] Starting service process...
echo Press Ctrl+C to stop service
echo.

cd web_interface
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

REM Service stopped handling
echo.
echo ========================================================
echo           Web Service Stopped
echo ========================================================
echo.
pause