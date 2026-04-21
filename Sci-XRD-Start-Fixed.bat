@echo off
title Sci-XRD System Startup (Fixed)
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
echo Step 3: Checking port availability...
netstat -ano | findstr ":8000" >nul
if not errorlevel 1 (
    echo WARNING: Port 8000 is in use!
    echo.
    echo Options:
    echo 1. Stop the existing service (recommended)
    echo 2. Use a different port
    echo.
    set /p choice="Choose option (1 or 2): "
    
    if "%choice%"=="2" (
        set /p newport="Enter new port number (e.g., 8080): "
        echo Using port %newport%
        set PORT=%newport%
    ) else (
        echo Stopping existing service...
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
        )
        echo OK: Port 8000 is now available
        set PORT=8000
    )
) else (
    echo OK: Port 8000 is available
    set PORT=8000
)

echo.
echo Step 4: Starting Web service...
echo.
echo Opening browser to: http://localhost:%PORT%
echo.
echo Features available:
echo - Single file XRD analysis
echo - Batch file processing  
echo - AI recommendations
echo - Professional charts
echo - Multiple export formats
echo.

start http://localhost:%PORT%

echo.
echo Step 5: Starting server...
echo Press Ctrl+C to stop the server
echo ============================================
echo.

cd web_interface
uvicorn app:app --host 0.0.0.0 --port %PORT% --reload

echo.
echo ============================================
echo      Service has stopped
echo ============================================
echo.
pause