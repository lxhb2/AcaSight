@echo off
title Start XRD System
color 0A

echo.
echo Starting Sci-XRD System...
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found
    pause
    exit /b 1
)

REM Check dependencies
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start
echo Starting server...
echo Open browser to: http://localhost:8000
echo Press Ctrl+C to stop
echo.

start http://localhost:8000

cd web_interface
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Server stopped
pause