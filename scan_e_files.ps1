[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$files = Get-ChildItem -Path E:\ -Recurse -ErrorAction SilentlyContinue | 
    Where-Object { $_.Length -gt 200MB } | 
    Sort-Object Length -Descending | 
    Select-Object -First 25

foreach ($f in $files) {
    $sizeMB = [math]::Round($f.Length/1MB, 0)
    Write-Output ("{0,6} MB | {1}" -f $sizeMB, $f.FullName)
}
