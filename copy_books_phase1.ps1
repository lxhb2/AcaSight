# Phase 1: Copy all book files from N10 to F:\N10图书整理\原始备份\
# This script copies from MTP device to local disk

$shell = New-Object -ComObject Shell.Application
$destBase = "F:\N10图书整理\原始备份"
$logFile = "F:\N10图书整理\copy_log.txt"

# Book file extensions to copy
$bookExts = @('.epub', '.pdf', '.mobi', '.azw3', '.txt', '.umd', '.cbz', '.cbr', '.djvu', '.doc', '.docx')

# Create destination
if (-not (Test-Path $destBase)) {
    New-Item -ItemType Directory -Path $destBase -Force | Out-Null
}

# Navigate to N10
$pc = $shell.NameSpace(17)
$n10 = $null
foreach ($item in $pc.Items()) {
    if ($item.Name -eq 'N10') { $n10 = $item; break }
}
if (-not $n10) { Write-Host "ERROR: N10 not found!"; exit 1 }

$n10Folder = $shell.NameSpace($n10)
$internalStorage = $null
foreach ($item in $n10Folder.Items()) {
    if ($item.Name -eq '内部共享存储空间') { $internalStorage = $item; break }
}
if (-not $internalStorage) { Write-Host "ERROR: Internal storage not found!"; exit 1 }

$internalFolder = $shell.NameSpace($internalStorage)

# Source folders to copy from
$sources = @('hvEpubReader', '我的文档', 'Download', 'documents', 'BaiduNetdisk')

function Log($msg) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    $line = "[$timestamp] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8
}

$totalCopied = 0
$totalSkipped = 0
$totalFailed = 0

function Copy-BooksFromMTP($mtpFolderObj, $srcName, $depth) {
    try {
        $items = $mtpFolderObj.Items()
    } catch {
        Log "  ERROR: Cannot list items in $srcName (depth=$depth): $_"
        return
    }
    
    foreach ($item in $items) {
        $isBook = $false
        foreach ($ext in $bookExts) {
            if ($item.Name.ToLower().EndsWith($ext)) {
                $isBook = $true
                break
            }
        }
        
        if ($isBook) {
            $destPath = Join-Path $destBase $item.Name
            if (Test-Path $destPath) {
                Log "  SKIP (exists): $($item.Name)"
                $script:totalSkipped++
                continue
            }
            
            # Create a temp dest folder object
            $destFolderObj = $shell.NameSpace($destBase)
            Log "  COPY: $($item.Name)"
            try {
                $copyFlags = 16 -bor 1024
                $destFolderObj.CopyHere($item, $copyFlags)
                # Wait for copy to complete (check file existence, max 120s)
                $waited = 0
                while (-not (Test-Path $destPath) -and $waited -lt 120) {
                    Start-Sleep -Seconds 2
                    $waited += 2
                }
                
                if (Test-Path $destPath) {
                    $size = (Get-Item $destPath).Length
                    $sizeMB = [math]::Round($size / 1MB, 2)
                    Log "  OK: $($item.Name) ($sizeMB MB)"
                    $script:totalCopied++
                } else {
                    Log "  FAIL (timeout): $($item.Name)"
                    $script:totalFailed++
                }
            } catch {
                Log "  FAIL: $($item.Name) - $_"
                $script:totalFailed++
            }
            # Small delay between copies to avoid overwhelming MTP
            Start-Sleep -Milliseconds 500
        }
        
        # Recurse into subfolders
        if ($item.IsFolder -and $depth -lt 5) {
            try {
                $subFolder = $shell.NameSpace($item)
                if ($subFolder) {
                    Copy-BooksFromMTP $subFolder "$srcName/$($item.Name)" ($depth + 1)
                }
            } catch {}
        }
    }
}

Log "=== Starting book copy from N10 to F:\N10图书整理\原始备份\ ==="
Log "Source folders: $($sources -join ', ')"

foreach ($src in $sources) {
    Log "`n--- Processing: $src ---"
    $found = $false
    foreach ($item in $internalFolder.Items()) {
        if ($item.Name -eq $src) {
            $found = $true
            $srcFolder = $shell.NameSpace($item)
            if ($srcFolder) {
                Copy-BooksFromMTP $srcFolder $src 0
            } else {
                Log "  ERROR: Cannot open folder $src"
            }
            break
        }
    }
    if (-not $found) {
        Log "  WARNING: Folder '$src' not found on device"
    }
}

Log "`n=== COPY COMPLETE ==="
Log "Copied: $totalCopied | Skipped: $totalFailed | Failed: $totalFailed"
