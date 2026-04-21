@echo off
title Sci-XRD System Startup
color 0A

echo.
echo ============================================
echo      Sci-XRD Analysis System v2.0.0
echo ============================================
echo.

cd /d "%~dp0"

echo Step 1: Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)
echo OK: Python is installed

echo.
echo Step 2: Checking dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install packages
        echo Please run: pip install fastapi uvicorn[standard]
        pause
        exit /b 1
    )
    echo OK: Packages installed
) else (
    echo OK: Packages already installed
)

echo.
echo Step 3: Starting Web service...
echo.
echo Opening browser to: http://localhost:8000
echo.
echo Features available:
echo - Single file XRD analysis
echo - Batch file processing  
echo - AI recommendations
echo - Professional charts
echo - Multiple export formats
echo.

start http://localhost:8000

echo.
echo Step 4: Starting server...
echo Press Ctrl+C to stop the server
echo ============================================
echo.

cd web_interface
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

echo.
echo ============================================
echo      Service has stopped
echo ============================================
echo.
pause