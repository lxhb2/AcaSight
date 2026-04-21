@echo off
echo ========================================
echo Python 学习平台 v2.3 启动器
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python
    pause
    exit /b 1
)

echo [2/3] 启动本地服务器...
start python -m http.server 8080

echo [3/3] 打开浏览器...
timeout /t 2 /nobreak >nul
start http://localhost:8080

echo.
echo ========================================
echo ✅ 启动完成！
echo 请访问: http://localhost:8080
echo ========================================
echo.
echo 使用说明:
echo - 学习模式: 点击左侧课程，在中间查看内容
echo - 练习模式: 点击"练习"标签，使用 Python 编辑器
echo - AI 助手: 右侧面板可与 AI 对话
echo.

pause
