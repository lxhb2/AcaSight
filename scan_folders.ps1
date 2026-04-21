[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$folders = Get-ChildItem -Path D:\ -Directory -ErrorAction SilentlyContinue

foreach ($folder in $folders) {
    $size = (Get-ChildItem -Path $folder.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $sizeGB = [math]::Round($size/1GB, 2)
    if ($sizeGB -gt 0.5) {
        Write-Output ("{0,8} GB | {1}" -f $sizeGB, $folder.Name)
    }
}
