@echo off
title Sci-XRD Unified Platform v3.0
color 0A

echo.
echo ============================================
echo      Sci-XRD Unified Analysis Platform
echo ============================================
echo.

REM This batch file is in the scripts folder
REM Change to project root directory (one level up)
cd /d "%~dp0.."

REM Now run the main batch file in the project root
call "Start-XRD-Platform.bat"