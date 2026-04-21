Remove-Item "H:\HermesPortable\HermesAgent\data\.hermes\*.bat" -Force -ErrorAction SilentlyContinue
Write-Host "[1] Cleaned all bat files"
Start-Sleep -Seconds 15
try {
    $r1 = Invoke-WebRequest -Uri "http://localhost:1420/api/hermes/dashboard" -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 15 -UseBasicParsing
    Write-Host "[2] Dashboard: $($r1.StatusCode)"
} catch { Write-Host "[2] Dashboard failed: $($_.Exception.Message)" }
try {
    $r2 = Invoke-WebRequest -Uri "http://localhost:1420/api/hermes/launch" -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 15 -UseBasicParsing
    Write-Host "[3] Chat: $($r2.StatusCode)"
} catch { Write-Host "[3] Chat failed: $($_.Exception.Message)" }
Start-Sleep -Seconds 2
$names = @("launch_chat.bat","launch_dashboard.bat")
foreach ($n in $names) {
    $p = "H:\HermesPortable\HermesAgent\data\.hermes\$n"
    if (Test-Path $p) {
        $c = Get-Content $p -Raw
        if ($c -match "Python312") {
            Write-Host "OK: $n" -ForegroundColor Green
        } else {
            Write-Host "FAIL: $n" -ForegroundColor Red
            Write-Host $c
        }
    } else {
        Write-Host "MISSING: $n" -ForegroundColor Red
    }
}
