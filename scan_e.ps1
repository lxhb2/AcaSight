[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$folders = Get-ChildItem -Path E:\ -Directory -ErrorAction SilentlyContinue

$results = @()
foreach ($folder in $folders) {
    $size = (Get-ChildItem -Path $folder.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $sizeGB = [math]::Round($size/1GB, 2)
    $results += [PSCustomObject]@{
        SizeGB = $sizeGB
        Name = $folder.Name
    }
}

$results | Sort-Object SizeGB -Descending | ForEach-Object {
    Write-Output ("{0,8} GB | {1}" -f $_.SizeGB, $_.Name)
}

$total = ($results | Measure-Object -Property SizeGB -Sum).Sum
Write-Output ("`n{0,8} GB | TOTAL" -f [math]::Round($total, 2))
