$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)

# Find N10 device
$n10 = $null
foreach ($item in $pc.Items()) {
    if ($item.Name -eq 'N10') {
        $n10 = $item
        break
    }
}

if (-not $n10) {
    Write-Host "N10 device not found!"
    exit
}

Write-Host "Found N10: $($n10.Name)"

# Navigate into N10 -> 内部共享存储空间
$n10Folder = $shell.NameSpace($n10)
Write-Host "N10 folder object: $($n10Folder -ne $null)"

$internalStorage = $null
foreach ($item in $n10Folder.Items()) {
    Write-Host "  Sub: $($item.Name)"
    if ($item.Name -eq '内部共享存储空间') {
        $internalStorage = $item
        break
    }
}

if (-not $internalStorage) {
    Write-Host "Internal storage not found!"
    exit
}

Write-Host "`nFound internal storage, scanning book-related folders..."

$internalFolder = $shell.NameSpace($internalStorage)
Write-Host "Internal folder object: $($internalFolder -ne $null)"

# Get all items in internal storage
$allItems = $internalFolder.Items()
Write-Host "Total items in internal storage: $($allItems.Count)"

# Scan book-related folders
$bookFolders = @('hvEpubReader', '汉王书库', 'bookshop', 'com.bilibili.comic', '我的文档', 'documents', 'Download', 'Mob', 'BaiduNetdisk')

function Scan-BookFolder($parentFolder, $targetName, $depth=0) {
    $prefix = "  " * $depth
    $items = $parentFolder.Items()
    $bookExts = @('.epub', '.pdf', '.mobi', '.azw3', '.txt', '.umd', '.cbz', '.cbr', '.djvu', '.doc', '.docx')
    
    foreach ($item in $items) {
        $isBook = $false
        foreach ($ext in $bookExts) {
            if ($item.Name.ToLower().EndsWith($ext)) {
                $isBook = $true
                break
            }
        }
        
        if ($isBook) {
            $size = ""
            try { $size = $parentFolder.GetDetailsOf($item, 2) } catch {}
            Write-Host "$prefix$($item.Name)  $size"
        }
        
        # Recurse into subfolders (limit depth)
        if ($item.IsFolder -and $depth -lt 4) {
            try {
                $subFolder = $shell.NameSpace($item)
                if ($subFolder) {
                    Scan-BookFolder $subFolder $targetName ($depth + 1)
                }
            } catch {}
        }
    }
}

foreach ($bookFolder in $bookFolders) {
    Write-Host "`n========== $bookFolder =========="
    $found = $false
    foreach ($item in $allItems) {
        if ($item.Name -eq $bookFolder) {
            $found = $true
            $folder = $shell.NameSpace($item)
            if ($folder) {
                Scan-BookFolder $folder $bookFolder 0
            } else {
                Write-Host "(could not open folder)"
            }
            break
        }
    }
    if (-not $found) {
        Write-Host "(not found)"
    }
}
