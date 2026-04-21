# Parse the source file and extract course data
$filePath = "F:\桌面\新建 文本文档 (2).txt"
$content = Get-Content $filePath -Raw -Encoding UTF8

# Find all target-title elements
$targets = @()
$pos = 0
while (($pos = $content.IndexOf('class="target-title">', $pos)) -ge 0) {
    $endPos = $content.IndexOf('<img', $pos)
    if ($endPos -gt $pos) {
        $targetText = $content.Substring($pos + 19, $endPos - pos - 19)  # 19 = length of 'class="target-title">'
        $targetText = $targetText -replace '<.*?>', '' -replace '^\s+|\s+$', ''
        $targets += $targetText
    }
    $pos++
}

# Find all class names
$classes = @()
$pos = 0
while (($pos = $content.IndexOf('课堂：', $pos)) -ge 0) {
    $endPos = $content.IndexOf('</div>', $pos)
    if ($endPos -gt $pos) {
        $className = $content.Substring($pos + 4, $endPos - pos - 4)
        $classes += $className
    }
    $pos++
}

# Combine into structured data
$result = @{
    courseName = "Python基础语法"
    targets = @()
}

$targetIdx = 0
$targetStart = 0

for ($i = 0; $i -lt $classes.Count; $i++) {
    # Determine which target this class belongs to
    $targetEnd = if ($i -lt $classes.Count - 1) {
        $content.IndexOf('课堂：', $content.IndexOf('课堂：', $content.IndexOf($classes[$i])) + 1)
    } else { $content.Length }
    
    if ($targetIdx -lt $targets.Count) {
        if ($result.targets.Count -eq 0 -or $result.targets[-1].name -ne $targets[$targetIdx]) {
            $result.targets += @{
                name = $targets[$targetIdx]
                classes = @()
            }
        }
        $result.targets[-1].classes += $classes[$i]
    }
}

$result | ConvertTo-Json -Depth 5
