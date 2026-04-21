@echo off
echo Testing Sci-XRD Launcher...
echo.

REM Check Python
python --version
if errorlevel 1 (
    echo Python not found!
    pause
    exit /b 1
)

echo Python OK
echo.

REM Check web_interface directory
if not exist "web_interface\app.py" (
    echo web_interface directory not found!
    pause
    exit /b 1
)

echo Web interface found
echo.

echo Test completed successfully!
echo You can now run: launch_sci_xrd.bat
pause