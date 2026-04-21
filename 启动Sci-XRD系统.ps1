# Sci-XRD 智能分析系统启动器 (PowerShell版本)
# 版本: 2.0.0

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║            Sci-XRD 智能分析系统启动器                ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║ 版本: 2.0.0 - 完整优化版                            ║" -ForegroundColor Yellow
Write-Host "║ 状态: 🟢 所有优化已完成                             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# 1. 检查Python环境
Write-Host "[1/5] 检查Python环境..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python环境正常: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python未找到"
    }
} catch {
    Write-Host "❌ 未找到Python，请先安装Python 3.8+" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

# 2. 检查必要文件
Write-Host "[2/5] 检查必要文件..." -ForegroundColor Cyan
$requiredFiles = @(
    "web_interface\app.py",
    "web_interface\start_server.py",
    "web_interface\config.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ 缺少必要文件:" -ForegroundColor Red
    foreach ($file in $missingFiles) {
        Write-Host "   - $file" -ForegroundColor Red
    }
    Read-Host "按Enter键退出"
    exit 1
}

if (-not (Test-Path "F:\桌面\pdf2_final_complete.db")) {
    Write-Host "⚠️ 警告: 数据库文件不存在，部分功能可能受限" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

Write-Host "✅ 必要文件检查通过" -ForegroundColor Green

# 3. 检查Python依赖
Write-Host "[3/5] 检查Python依赖..." -ForegroundColor Cyan
try {
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 依赖已安装" -ForegroundColor Green
    } else {
        Write-Host "⏳ 安装FastAPI依赖..." -ForegroundColor Yellow
        pip install fastapi uvicorn[standard] 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "依赖安装失败"
        }
        Write-Host "✅ 依赖安装完成" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ 依赖检查失败: $_" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

# 4. 启动Web服务
Write-Host "[4/5] 启动Web服务..." -ForegroundColor Cyan
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                Web服务启动中...                      ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║ 服务地址: http://localhost:8000                      ║" -ForegroundColor Yellow
Write-Host "║ API文档: http://localhost:8000/docs                  ║" -ForegroundColor Yellow
Write-Host "║ 状态监控: http://localhost:8000/status               ║" -ForegroundColor Yellow
Write-Host "║ 实时图表: http://localhost:8000/analyzer             ║" -ForegroundColor Yellow
Write-Host "║ 批量处理: http://localhost:8000/batch                ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "系统功能:" -ForegroundColor Cyan
Write-Host "  • 单文件XRD分析" -ForegroundColor White
Write-Host "  • 批量文件处理" -ForegroundColor White
Write-Host "  • AI智能推荐" -ForegroundColor White
Write-Host "  • 专业图表生成" -ForegroundColor White
Write-Host "  • 多格式导出 (Origin/Word/Excel)" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 打开浏览器
try {
    Start-Process "http://localhost:8000"
    Write-Host "✅ 浏览器已打开" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 无法自动打开浏览器，请手动访问" -ForegroundColor Yellow
}

# 启动服务
Set-Location "web_interface"
try {
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
} catch {
    Write-Host "❌ 服务启动失败: $_" -ForegroundColor Red
}

# 服务停止后的处理
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                Web服务已停止                         ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Read-Host "按Enter键退出"