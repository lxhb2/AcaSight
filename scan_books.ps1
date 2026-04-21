$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)
$n10Path = '::{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\\?\usb#vid_2207&pid_0007#9615524030000068#{6ac27878-a6fa-4155-ba85-f98f491d4f33}\SID-{10001,,56906219520}'
$internal = $shell.NameSpace($n10Path)

# Book-related folders to scan
$bookFolders = @('hvEpubReader', '汉王书库', 'bookshop', 'com.bilibili.comic', '我的文档', 'documents', 'Download')

function Scan-Folder($folderObj, $depth=0) {
    $prefix = "  " * $depth
    $items = $folderObj.Items()
    foreach ($item in $items) {
        $ext = ""
        if ($item.Name -match '\.(\w+)$') { $ext = $Matches[1].ToLower() }
        $size = ""
        try { $size = $folderObj.GetDetailsOf($item, 2) } catch {}
        Write-Host "$prefix$($item.Name)  $size"
        
        # Only recurse into subfolders, and limit depth
        if ($item.IsFolder -and $item.IsFileSystem -eq $false -and $depth -lt 3) {
            # It's a virtual/shell folder
            try {
                $subFolder = $shell.NameSpace($item)
                if ($subFolder -and $depth -lt 3) {
                    Scan-Folder $subFolder ($depth + 1)
                }
            } catch {}
        } elseif ($item.IsFolder -and $depth -lt 3) {
            try {
                $subFolder = $shell.NameSpace($item)
                if ($subFolder -and $depth -lt 3) {
                    Scan-Folder $subFolder ($depth + 1)
                }
            } catch {}
        }
    }
}

foreach ($bookFolder in $bookFolders) {
    Write-Host "`n========== $bookFolder =========="
    $found = $false
    foreach ($item in $internal.Items()) {
        if ($item.Name -eq $bookFolder) {
            $found = $true
            $folder = $shell.NameSpace($item)
            if ($folder) {
                Scan-Folder $folder 0
            }
            break
        }
    }
    if (-not $found) {
        Write-Host "(folder not found)"
    }
}
