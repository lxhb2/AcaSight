$content = Get-Content "F:\桌面\新建 文本文档 (2).txt" -Raw -Encoding UTF8

$chapters = @()
$searchStr = '<span class="level-title">第'
$idx = 0

while (($idx = $content.IndexOf($searchStr, $idx)) -ge 0) {
    $levelEnd = $content.IndexOf('关', $idx)
    if ($levelEnd -gt $idx) {
        $levelNum = $content.Substring($idx + 27, $levelEnd - $idx - 27)
        
        $classStart = $content.IndexOf('课堂：', $idx)
        if ($classStart -gt 0 -and $classStart -lt $idx + 200) {
            $classEnd = $content.IndexOf('</div>', $classStart)
            if ($classEnd -gt $classStart) {
                $className = $content.Substring($classStart + 4, $classEnd - $classStart - 4)
                $chapters += @{level=[int]$levelNum; name=$className}
            }
        }
    }
    $idx++
}

$chapters | Sort-Object level | ForEach-Object { Write-Host "第$($_.level)关 - $($_.name)" }
