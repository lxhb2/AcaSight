@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo   Pulse Learning System - 启动器
echo ================================================
echo.
echo 选择运行模式:
echo   [1] Web UI   (浏览器界面，流式响应)
echo   [2] CLI      (命令行界面)
echo   [3] 测试     (快速测试)
echo.
set /p choice=请输入选项 [1/2/3]:

if "%choice%"=="1" goto web
if "%choice%"=="2" goto cli
if "%choice%"=="3" goto test

:web
echo.
echo 正在启动 Web UI...
echo 请用浏览器打开 http://localhost:5050
python web_ui.py
goto end

:cli
echo.
echo 正在启动 CLI...
python cli.py
goto end

:test
echo.
echo 运行测试...
python scripts/test_multi_model.py
pause
goto end

:end
pause
