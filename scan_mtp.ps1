$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)
Write-Host "=== This PC Items ==="
foreach ($item in $pc.Items()) {
    Write-Host "Device: $($item.Name) | Path: $($item.Path)"
    if ($item.Name -like "*N10*") {
        Write-Host "  -> Found N10 device!"
        $device = $item
        # Try to enumerate folders inside the device
        $deviceFolder = $shell.NameSpace($device)
        if ($deviceFolder) {
            Write-Host "  Subfolders:"
            foreach ($sub in $deviceFolder.Items()) {
                Write-Host "    - $($sub.Name) | $($sub.Path)"
                if ($sub.Name -like "*内部*" -or $sub.Name -like "*Internal*") {
                    $internal = $shell.NameSpace($sub)
                    if ($internal) {
                        Write-Host "      Internal storage folders:"
                        foreach ($folder in $internal.Items()) {
                            Write-Host "        - $($folder.Name)"
                        }
                    }
                }
            }
        }
    }
}
