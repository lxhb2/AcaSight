$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)
Write-Host "=== This PC Devices ==="
foreach ($item in $pc.Items()) {
    Write-Host "  $($item.Name) | Path: $($item.Path)"
}
