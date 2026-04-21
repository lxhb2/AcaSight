@echo off
title Sci-XRD Unified Platform v3.0
color 0A

echo.
echo ============================================
echo      Sci-XRD Unified Analysis Platform
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
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Installing PyQt6...
    pip install PyQt6 >nul 2>&1
)
echo OK: Dependencies checked

echo.
echo Step 3: Creating test data...
if not exist "test_xrd_data.csv" (
    (
        echo 2Theta,Intensity
        for /l %%i in (1000,5,8000) do (
            set /a angle=%%i/100
            set /a intensity=1000 + %%i %% 500
            echo !angle!.!angle!,!intensity!
        )
    ) > test_xrd_data.csv 2>&1
)
echo OK: Test data ready

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

python xrd_unified_platform.py

echo.
echo ============================================
echo      Platform closed
echo ============================================
echo.
pause
