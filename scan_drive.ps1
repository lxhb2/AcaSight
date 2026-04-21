[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$files = Get-ChildItem -Path D:\ -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 100MB } | 
    Sort-Object Length -Descending | 
    Select-Object -First 40

foreach ($f in $files) {
    $sizeMB = [math]::Round($f.Length/1MB, 0)
    Write-Output ("{0,6} MB | {1}" -f $sizeMB, $f.FullName)
}
