@echo off
title Sci-XRD 一体化分析平台 - 所有功能集成
color 0A

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║                                                       ║
echo ║         Sci-XRD 一体化分析平台 v3.0                  ║
echo ║         所有功能集成 - 单一界面操作                  ║
echo ║                                                       ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/6] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   错误: Python未安装!
    echo   请从 https://www.python.org/downloads/ 安装Python 3.8+
    echo   安装时请勾选"Add Python to PATH"
    pause
    exit /b 1
)
echo   成功: Python已安装

echo.
echo [2/6] 检查必要依赖...
set DEPENDENCIES=PyQt6 numpy pandas matplotlib

for %%d in (%DEPENDENCIES%) do (
    python -c "import %%d" >nul 2>&1
    if errorlevel 1 (
        echo   安装 %%d...
        pip install %%d --quiet >nul 2>&1
        if errorlevel 1 (
            echo   错误: 安装 %%d 失败
            echo   请手动运行: pip install %%d
            pause
            exit /b 1
        )
        echo   成功: %%d 已安装
    ) else (
        echo   已安装: %%d
    )
)

echo.
echo [3/6] 检查可选依赖...
python -c "import sci_xrd" >nul 2>&1
if errorlevel 1 (
    echo   提示: sci_xrd模块未安装，使用模拟分析功能
) else (
    echo   已安装: sci_xrd核心算法
)

python -c "import pdf2_db" >nul 2>&1
if errorlevel 1 (
    echo   提示: PDF2数据库模块未安装，使用模拟数据库
) else (
    echo   已安装: PDF2数据库
)

echo.
echo [4/6] 准备测试数据...
if not exist "test_xrd_data.csv" (
    echo   创建测试数据文件...
    echo 2Theta,Intensity > test_xrd_data.csv
    for /l %%i in (10,1,80) do (
        echo %%i.00,1000 >> test_xrd_data.csv
    )
    echo   成功: 测试数据已创建
) else (
    echo   已存在: 测试数据文件
)

echo.
echo [5/6] 平台功能概览...
echo   • 单一界面集成所有功能
echo   • 支持多种数据格式导入
echo   • 实时图表显示与分析
echo   • 峰位检测与物相鉴定
echo   • 定量分析与结果导出
echo   • 批处理与自定义设置
echo.

echo [6/6] 启动一体化平台...
echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║                   使用说明                           ║
echo ╠═══════════════════════════════════════════════════════╣
echo ║ 1. 点击"选择XRD数据文件"导入数据                    ║
echo ║ 2. 在左侧面板设置分析参数                          ║
echo ║ 3. 点击"快速分析"或"完整分析"                      ║
echo ║ 4. 在右侧面板查看分析结果                          ║
echo ║ 5. 使用"导出结果"保存分析报告                      ║
echo ║ 6. 详细指南见: 一体化平台使用指南.md                ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
echo 正在启动主界面...
echo 请稍候...
echo.

timeout /t 2 /nobreak >nul

start "" "一体化平台使用指南.md"

python xrd_unified_platform.py

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║                平台已关闭                            ║
echo ╠═══════════════════════════════════════════════════════╣
echo ║ 如需再次启动:                                        ║
echo ║   1. 双击本文件                                      ║
echo ║   2. 或运行: python xrd_unified_platform.py          ║
echo ║                                                      ║
echo ║ 技术支持:                                            ║
echo ║   • 文档: 一体化平台使用指南.md                      ║
echo ║   • 测试数据: test_xrd_data.csv                      ║
echo ║   • 问题反馈: 提供错误截图和日志                    ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
pause