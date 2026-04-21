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

$n10Folder = $shell.NameSpace($n10)
$internalStorage = $null
foreach ($item in $n10Folder.Items()) {
    if ($item.Name -eq '内部共享存储空间') {
        $internalStorage = $item
        break
    }
}

$internalFolder = $shell.NameSpace($internalStorage)

# Find 汉王书库 and Pictures
foreach ($item in $internalFolder.Items()) {
    if ($item.Name -eq '汉王书库') {
        Write-Host "========== 汉王书库 =========="
        $folder = $shell.NameSpace($item)
        if ($folder) {
            foreach ($sub in $folder.Items()) {
                Write-Host "  $($sub.Name)"
                if ($sub.IsFolder) {
                    $subFolder = $shell.NameSpace($sub)
                    if ($subFolder) {
                        foreach ($file in $subFolder.Items()) {
                            $size = ""
                            try { $size = $folder.GetDetailsOf($file, 2) } catch {}
                            Write-Host "    $($file.Name)  $size"
                        }
                    }
                }
            }
        }
    }
    if ($item.Name -eq 'Pictures') {
        Write-Host "`n========== Pictures =========="
        $folder = $shell.NameSpace($item)
        if ($folder) {
            foreach ($sub in $folder.Items()) {
                Write-Host "  $($sub.Name)"
            }
        }
    }
    if ($item.Name -eq 'Office') {
        Write-Host "`n========== Office =========="
        $folder = $shell.NameSpace($item)
        if ($folder) {
            foreach ($sub in $folder.Items()) {
                Write-Host "  $($sub.Name)"
            }
        }
    }
}
