@echo off
chcp 65001 >nul
title Sci-XRD 智能分析系统 v2.0.0
color 0A

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║            Sci-XRD 智能分析系统启动器                ║
echo ╠══════════════════════════════════════════════════════╣
echo ║ 版本: 2.0.0 - 完整优化版                            ║
echo ║ 状态: 🟢 所有优化已完成                             ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 检查Python环境
echo [1/5] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)
echo ✅ Python环境正常

REM 检查必要文件
echo [2/5] 检查必要文件...
if not exist "web_interface\app.py" (
    echo ❌ 缺少Web界面文件
    pause
    exit /b 1
)

if not exist "F:\桌面\pdf2_final_complete.db" (
    echo ⚠️ 警告: 数据库文件不存在，部分功能可能受限
    timeout /t 2 >nul
)

echo ✅ 必要文件检查通过

REM 安装依赖（如果需要）
echo [3/5] 检查Python依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ⏳ 安装FastAPI依赖...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已安装
)

REM 启动Web服务
echo [4/5] 启动Web服务...
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                Web服务启动中...                      ║
echo ╠══════════════════════════════════════════════════════╣
echo ║ 服务地址: http://localhost:8000                      ║
echo ║ API文档: http://localhost:8000/docs                  ║
echo ║ 状态监控: http://localhost:8000/status               ║
echo ╚══════════════════════════════════════════════════════╝
echo.
echo 按 Ctrl+C 停止服务
echo.

REM 启动服务
cd web_interface
start "" "http://localhost:8000"
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

REM 服务停止后的处理
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                Web服务已停止                         ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause