@echo off
title Sci-XRD 一体化分析平台 v3.0
color 0A

echo.
echo ============================================
echo      Sci-XRD 一体化分析平台 v3.0
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
    if errorlevel 1 (
        echo ERROR: Failed to install PyQt6
        echo Please run: pip install PyQt6
        pause
        exit /b 1
    )
    echo OK: PyQt6 installed
) else (
    echo OK: PyQt6 already installed
)

python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo Installing numpy...
    pip install numpy >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install numpy
        echo Please run: pip install numpy
        pause
        exit /b 1
    )
    echo OK: numpy installed
) else (
    echo OK: numpy already installed
)

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing pandas...
    pip install pandas >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install pandas
        echo Please run: pip install pandas
        pause
        exit /b 1
    )
    echo OK: pandas installed
) else (
    echo OK: pandas already installed
)

python -c "import matplotlib" >nul 2>&1
if errorlevel 1 (
    echo Installing matplotlib...
    pip install matplotlib >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install matplotlib
        echo Please run: pip install matplotlib
        pause
        exit /b 1
    )
    echo OK: matplotlib installed
) else (
    echo OK: matplotlib already installed
)

echo.
echo Step 3: Starting Sci-XRD Unified Platform...
echo.
echo Features:
echo - Single interface for all XRD analysis
echo - Data import from multiple formats
echo - Peak detection and phase identification
echo - Quantitative analysis
echo - Professional charts and reports
echo - Batch processing capability
echo.
echo ============================================
echo.

python xrd_unified_platform.py

echo.
echo ============================================
echo      Platform has been closed
echo ============================================
echo.
pause