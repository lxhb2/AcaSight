# Try creating folders directly in the internal storage root
# And try MoveHere to move files

$shell = New-Object -ComObject Shell.Application
$pc = $shell.NameSpace(17)

$n10 = $null
foreach ($item in $pc.Items()) {
    if ($item.Name -eq 'N10') { $n10 = $item; break }
}
$n10Folder = $shell.NameSpace($n10)

$internalStorage = $null
foreach ($item in $n10Folder.Items()) {
    if ($item.Name -eq '内部共享存储空间') { $internalStorage = $item; break }
}

# Try to use the internal storage path directly for NewFolder
$internalFolder = $shell.NameSpace($internalStorage)
Write-Host "Internal folder: $($internalFolder -ne $null)"
Write-Host "Internal folder title: $($internalFolder.Title)"

# List existing items
Write-Host "`nExisting folders in internal storage:"
foreach ($item in $internalFolder.Items()) {
    Write-Host "  $($item.Name) - IsFolder: $($item.IsFolder)"
}

# Try creating a test folder
Write-Host "`nAttempting to create test folder '图书分类'..."
try {
    $internalFolder.NewFolder('图书分类')
    Write-Host "Success!"
} catch {
    Write-Host "Failed: $_"
}

# Try alternative: check if 我的文档 can have subfolders
$myDoc = $null
foreach ($item in $internalFolder.Items()) {
    if ($item.Name -eq '我的文档') { $myDoc = $item; break }
}

if ($myDoc) {
    $myDocFolder = $shell.NameSpace($myDoc)
    Write-Host "`n我的文档 folder object: $($myDocFolder -ne $null)"
    if ($myDocFolder) {
        Write-Host "Items in 我的文档:"
        foreach ($item in $myDocFolder.Items()) {
            Write-Host "  $($item.Name)"
        }
        Write-Host "`nAttempting to create test folder in 我的文档..."
        try {
            $myDocFolder.NewFolder('测试分类')
            Write-Host "Success!"
        } catch {
            Write-Host "Failed: $_"
        }
    }
}
