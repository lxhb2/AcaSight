# Step 1: Create category folders under 我的文件 on N10
$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)

# Find N10 device
$n10 = $null
foreach ($item in $pc.Items()) {
    if ($item.Name -eq 'N10') { $n10 = $item; break }
}
$n10Folder = $shell.NameSpace($n10)

# Find 内部共享存储空间
$internalStorage = $null
foreach ($item in $n10Folder.Items()) {
    if ($item.Name -eq '内部共享存储空间') { $internalStorage = $item; break }
}
$internalFolder = $shell.NameSpace($internalStorage)

# Find or create 我的文件
$myFiles = $null
foreach ($item in $internalFolder.Items()) {
    if ($item.Name -eq '我的文件') { $myFiles = $item; break }
}

if (-not $myFiles) {
    Write-Host "Creating 我的文件 folder..."
    $internalFolder.NewFolder('我的文件')
    Start-Sleep -Seconds 3
    # Re-find
    foreach ($item in $internalFolder.Items()) {
        if ($item.Name -eq '我的文件') { $myFiles = $item; break }
    }
}

$myFilesFolder = $shell.NameSpace($myFiles)
Write-Host "我的文件 folder ready: $($myFilesFolder -ne $null)"

# Create category folders
$categories = @(
    '科普百科',
    '中国古典文学',
    '外国文学',
    '历史军事',
    '国学经典',
    '经济理财',
    '心理成长',
    '学习方法',
    '考研备考',
    '专业技术',
    '摄影艺术',
    '健康中医'
)

foreach ($cat in $categories) {
    # Check if already exists
    $exists = $false
    foreach ($item in $myFilesFolder.Items()) {
        if ($item.Name -eq $cat) { $exists = $true; break }
    }
    if (-not $exists) {
        Write-Host "Creating folder: $cat"
        $myFilesFolder.NewFolder($cat)
        Start-Sleep -Seconds 2
    } else {
        Write-Host "Folder exists: $cat"
    }
}

Write-Host "`nDone creating folders!"
