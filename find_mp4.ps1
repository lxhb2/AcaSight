[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$files = Get-ChildItem -Path 'D:\四季如歌' -Recurse -Filter '*.mp4' -ErrorAction SilentlyContinue
foreach ($f in $files) {
    $sizeMB = [math]::Round($f.Length/1MB, 0)
    if ($sizeMB -gt 100) {
        Write-Output ("{0,6} MB | {1}" -f $sizeMB, $f.FullName)
    }
}
