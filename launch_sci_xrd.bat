@echo off
title Sci-XRD System Launcher
color 0A

echo.
echo ============================================
echo      Sci-XRD Analysis System v2.0.0
echo ============================================
echo.

REM Set current directory
cd /d "%~dp0"

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)
echo OK: Python found

REM Check dependencies
echo [2/4] Checking dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing FastAPI and Uvicorn...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        echo Try: pip install fastapi uvicorn[standard]
        pause
        exit /b 1
    )
    echo OK: Dependencies installed
) else (
    echo OK: Dependencies ready
)

REM Start service
echo [3/4] Starting Web service...
echo.
echo Opening browser to: http://localhost:8000
echo.
echo System Features:
echo - XRD file analysis
echo - Batch processing
echo - AI recommendations
echo - Professional charts
echo - Multiple export formats
echo.

REM Open browser
start http://localhost:8000

REM Start server
echo [4/4] Starting server...
echo Press Ctrl+C to stop
echo ============================================
echo.

cd web_interface
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

echo.
echo ============================================
echo      Service stopped
echo ============================================
echo.
pause