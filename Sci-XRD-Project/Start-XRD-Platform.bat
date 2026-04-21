@echo off
title Sci-XRD Unified Platform v3.0
color 0A

echo.
echo ============================================
echo      Sci-XRD Unified Analysis Platform
echo ============================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
echo Script directory: %SCRIPT_DIR%

REM Change to project root directory (one level up from scripts)
cd /d "%SCRIPT_DIR%"
echo Changed to project root: %CD%

echo.
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
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing PyQt6...
    pip install PyQt6 >nul 2>&1
)
python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo Installing numpy...
    pip install numpy >nul 2>&1
)
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing pandas...
    pip install pandas >nul 2>&1
)
python -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo Installing matplotlib...
    pip install matplotlib >nul 2>&1
)
echo OK: Dependencies checked

echo.
echo Step 3: Checking test data...
if not exist "data\test_xrd_data.csv" (
    echo Creating test data in data\ folder...
    if not exist "data" mkdir data
    (
        echo 2Theta,Intensity
        for /l %%i in (1000,5,8000) do (
            set /a angle=%%i/100
            set /a intensity=1000 + %%i %% 500
            echo !angle!.!angle!,!intensity!
        )
    ) > "data\test_xrd_data.csv" 2>&1
    echo OK: Test data created at data\test_xrd_data.csv
) else (
    echo OK: Test data already exists
)

echo.
echo Step 4: Starting Sci-XRD Unified Platform...
echo.
echo Features:
echo - All-in-one interface
echo - Data import from multiple formats
echo - Peak detection and phase identification
echo - Quantitative analysis
echo - Professional charts
echo - Batch processing
echo.
echo ============================================
echo.

REM Run the main Python application from src folder
python src\xrd_unified_platform.py

echo.
echo ============================================
echo      Platform closed
echo ============================================
echo.
pause