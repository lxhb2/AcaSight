@echo off
chcp 65001 >nul
title Sci-XRD 智能分析系统 - 一键启动
color 0A

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║            Sci-XRD 智能分析系统                      ║
echo ╠══════════════════════════════════════════════════════╣
echo ║ 版本: 2.0.0 - 双击启动版                            ║
echo ║ 功能: 一键启动完整分析系统                          ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 切换到当前目录
cd /d "%~dp0"

REM 检查Python
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到Python，请先安装Python 3.8+
    echo.
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✅ Python环境正常

REM 检查依赖
echo [2/4] 检查系统依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ⏳ 安装必要依赖...
    pip install fastapi uvicorn[standard] >nul 2>&1
    if errorlevel 1 (
        echo ❌ 依赖安装失败，请手动安装:
        echo pip install fastapi uvicorn[standard]
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已安装
)

REM 启动系统
echo [3/4] 启动Web服务...
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                Web服务启动成功！                     ║
echo ╠══════════════════════════════════════════════════════╣
echo ║ 正在打开浏览器...                                   ║
echo ║                                                     ║
echo ║ 如果浏览器未自动打开，请手动访问:                   ║
echo ║   http://localhost:8000                             ║
echo ║                                                     ║
echo ║ 主要功能:                                           ║
echo ║   • 单文件XRD分析                                   ║
echo ║   • 批量文件处理                                    ║
echo ║   • AI智能推荐                                      ║
echo ║   • 专业图表生成                                    ║
echo ║   • 多格式导出                                      ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM 打开浏览器
start "" "http://localhost:8000"

REM 启动Web服务
echo [4/4] 启动服务进程...
echo 按 Ctrl+C 停止服务
echo.

cd web_interface
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

REM 服务停止后的处理
echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║                Web服务已停止                         ║
echo ╚══════════════════════════════════════════════════════╝
echo.
pause