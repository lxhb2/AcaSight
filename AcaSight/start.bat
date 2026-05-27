@echo off
chcp 65001 >nul
title AcaSight - 学术视界

echo ========================================
echo   AcaSight 学术视界 - 快速启动脚本
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo [1/4] 检查依赖...
cd /d "%~dp0"

:: 安装后端依赖（如需要）
if not exist "backend\venv" (
    echo 创建 Python 虚拟环境...
    python -m venv backend\venv
)

echo [2/4] 激活虚拟环境并安装后端依赖...
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt >nul 2>&1

echo [3/4] 安装前端依赖（如需要）...
cd frontend
if not exist "node_modules" (
    npm install
)
cd ..

echo [4/4] 启动服务...
echo.

:: 启动后端（在新窗口）
start "AcaSight Backend (端口 8000)" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: 等待后端启动
timeout /t 3 /nobreak >nul

:: 启动前端
start "AcaSight Frontend (端口 5173)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   启动完成！
echo.
echo   前端界面:  http://localhost:5173
echo   后端 API:  http://localhost:8000
echo   API 文档:  http://localhost:8000/api/docs
echo ========================================
echo.
echo 按任意键打开浏览器...
pause >nul

start http://localhost:5173
