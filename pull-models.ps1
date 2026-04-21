# Ollama 模型下载脚本 - 持久运行版
# 持续尝试下载所有缺失的模型，直到全部完成

$ErrorActionPreference = "SilentlyContinue"

# 需要下载的模型列表
$models = @(
    @{ name = "qwen3.5:4b"; size = "3.2 GB"; priority = 1 },
    @{ name = "qwen3-vl:4b"; size = "3.1 GB"; priority = 2 },
    @{ name = "qwen3:4b"; size = "2.5 GB"; priority = 3 },
    @{ name = "gemma3:1b"; size = "778 MB"; priority = 4 },
    @{ name = "nomic-embed-text"; size = "262 MB"; priority = 5 }
)

$logFile = "$env:USERPROFILE\.qclaw\workspace\logs\ollama-pull.log"
$maxRetries = 999

# 确保日志目录存在
$logDir = Split-Path $logFile -Parent
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log {
    param($msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Out-File -Append -FilePath $logFile -Encoding utf8
    Write-Host "$ts $msg"
}

# 每次只下载一个模型，避免网络冲突
foreach ($model in ($models | Sort-Object priority)) {
    $attempts = 0
    $done = $false

    while (!$done -and $attempts -lt $maxRetries) {
        $attempts++
        Write-Log "[$($model.name)] 下载尝试 #$attempts ..."

        # 先检查是否已下载
        $list = ollama list 2>&1
        if ($list -match $model.name) {
            Write-Log "[$($model.name)] 已存在，跳过"
            $done = $true
            continue
        }

        # 尝试下载
        $out = ollama pull $model.name 2>&1
        $exitCode = $LASTEXITCODE

        # 检查结果
        if ($exitCode -eq 0 -and !(($out -match "Error"))) {
            Write-Log "[$($model.name)] 下载成功！"
            $done = $true
        } else {
            Write-Log "[$($model.name)] 下载失败 (attempt $attempts)，10秒后重试..."
            if ($out -match "Error") {
                Write-Log "  错误: $($out -match 'Error' | ForEach-Object { $_ })"
            }
            Start-Sleep -Seconds 10
        }
    }

    if (!$done) {
        Write-Log "[$($model.name)] 达到最大重试次数，跳过"
    }
}

Write-Log "=== 全部完成 ==="
Write-Log "当前模型列表:"
ollama list 2>&1 | Out-File -Append -FilePath $logFile -Encoding utf8
