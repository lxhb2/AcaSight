# 复制课程文件到 data/courses 目录
# 用法: 双击运行此脚本

 = "D:\百度网盘下载\风\风变：语法+爬虫+自动化+分析\风变：语法+爬虫+自动化+分析"
 = Split-Path -Parent System.Management.Automation.InvocationInfo.MyCommand.Path
 = Join-Path  "data\courses"

# 创建目标目录
if (!(Test-Path )) {
    New-Item -ItemType Directory -Path  -Force | Out-Null
}

Write-Host "正在复制课程文件..."
Write-Host "源目录: "
Write-Host "目标目录: "

# 复制文件夹
 = @("【1】Python基础语法", "【2】Python爬虫精进", "【3】python办公自动化", "【4】Python数据分析实训课")

foreach ( in ) {
     = Join-Path  
     = Join-Path  
    
    if (Test-Path ) {
        Write-Host "复制: "
        Copy-Item -Path  -Destination  -Recurse -Force
    }
}

Write-Host ""
Write-Host "✅ 课程文件复制完成!"
Write-Host "请双击 start.py 启动学习平台"
Write-Host ""
Write-Host "注意: 如果启动器无法运行，请确保已安装 Python"
Write-Host "下载地址: https://www.python.org/downloads/"

Pause
