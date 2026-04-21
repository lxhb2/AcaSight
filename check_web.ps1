$nmDir = "H:\HermesPortable\HermesAgent\app\web\node_modules"
if (Test-Path $nmDir) {
    $pkgCount = (Get-ChildItem $nmDir -Directory -ErrorAction SilentlyContinue).Count
    Write-Host "node_modules packages: $pkgCount"
    $pkgs = @("typescript","vite","react","lucide-react","tailwindcss")
    foreach ($p in $pkgs) {
        $path = Join-Path $nmDir $p
        if (Test-Path $path) {
            Write-Host "  $p : OK"
        } else {
            Write-Host "  $p : MISSING"
        }
    }
    $binDir = Join-Path $nmDir ".bin"
    if (Test-Path $binDir) {
        Write-Host "`n.bins:"
        Get-ChildItem $binDir -ErrorAction SilentlyContinue | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.Name)" }
    }
} else {
    Write-Host "node_modules not found"
}

Write-Host "`n=== Running tsc from .bin ==="
$tsc = Join-Path $nmDir ".bin\tsc.cmd"
if (Test-Path $tsc) {
    Write-Host "Found: $tsc"
    & $tsc -b 2>&1 | Select-Object -Last 20
} else {
    Write-Host "tsc.cmd not found"
    $tscNpx = Join-Path $nmDir ".bin\tsc"
    if (Test-Path $tscNpx) {
        Write-Host "Found (no ext): $tscNpx"
    } else {
        Write-Host "No tsc found at all"
    }
}
