@echo off
chcp 65001 >nul
title Sci-XRD Pro - 专业XRD分析平台
color 0A

echo.
echo ========================================
echo      Sci-XRD Pro 启动器
echo ========================================
echo.

REM 检查Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查Python版本
python -c "import sys; exit(0) if sys.version_info >= (3, 8) else exit(1)" >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] Python版本过低，需要3.8+
    echo 当前版本:
    python --version
    pause
    exit /b 1
)

REM 检查依赖
echo [1/4] 检查依赖包...
python -c "
try:
    import PyQt6, numpy, scipy, matplotlib, pandas, aiohttp, chardet
    print('✓ 所有依赖包已安装')
except ImportError as e:
    print(f'❌ 缺失依赖包: {e}')
    exit(1)
" >nul 2>nul

if %errorlevel% neq 0 (
    echo [警告] 缺少依赖包，正在尝试安装...
    
    echo 安装PyQt6...
    pip install PyQt6 -q
    
    echo 安装numpy...
    pip install numpy -q
    
    echo 安装scipy...
    pip install scipy -q
    
    echo 安装matplotlib...
    pip install matplotlib -q
    
    echo 安装pandas...
    pip install pandas -q
    
    echo 安装aiohttp...
    pip install aiohttp -q
    
    echo 安装chardet...
    pip install chardet -q
    
    echo ✓ 依赖包安装完成
)

REM 检查Ollama
echo [2/4] 检查AI服务...
curl -s http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% equ 0 (
    echo ✓ Ollama服务可用
) else (
    echo ⚠ Ollama服务不可用，AI功能将受限
    echo   请运行: ollama serve
)

REM 启动应用程序
echo [3/4] 启动应用程序...
echo.

REM 设置环境变量
set PYTHONPATH=%~dp0;%PYTHONPATH%
set SCI_XRD_HOME=%~dp0

REM 运行主程序
cd /d "%~dp0"
python run.py %*

if %errorlevel% neq 0 (
    echo.
    echo [错误] 应用程序启动失败
    echo 请检查:
    echo 1. 依赖包是否安装正确
    echo 2. Python版本是否为3.8+
    echo 3. 是否有足够的权限
    pause
    exit /b %errorlevel%
)

echo.
echo [4/4] 应用程序已退出
echo ========================================
echo.

pause