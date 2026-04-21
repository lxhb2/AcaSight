# Sci-XRD System Launcher (PowerShell)
# Version: 2.0.0

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "      Sci-XRD Analysis System v2.0.0" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Step 1: Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python not found"
    }
} catch {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check dependencies
Write-Host "`nStep 2: Checking dependencies..." -ForegroundColor Cyan
try {
    python -c "import fastapi" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: Dependencies already installed" -ForegroundColor Green
    } else {
        Write-Host "Installing required packages..." -ForegroundColor Yellow
        pip install fastapi uvicorn[standard] 2>$null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install packages"
        }
        Write-Host "OK: Packages installed" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: Dependency check failed: $_" -ForegroundColor Red
    Write-Host "Please run: pip install fastapi uvicorn[standard]" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check web interface
Write-Host "`nStep 3: Checking system files..." -ForegroundColor Cyan
if (-not (Test-Path "web_interface\app.py")) {
    Write-Host "ERROR: Web interface not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK: System files found" -ForegroundColor Green

# Start service
Write-Host "`nStep 4: Starting Web service..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening browser to: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""
Write-Host "System Features:" -ForegroundColor White
Write-Host "- Single file XRD analysis" -ForegroundColor Gray
Write-Host "- Batch file processing" -ForegroundColor Gray
Write-Host "- AI recommendations" -ForegroundColor Gray
Write-Host "- Professional charts" -ForegroundColor Gray
Write-Host "- Multiple export formats" -ForegroundColor Gray
Write-Host ""

# Open browser
try {
    Start-Process "http://localhost:8000"
    Write-Host "Browser opened successfully" -ForegroundColor Green
} catch {
    Write-Host "Note: Could not open browser automatically" -ForegroundColor Yellow
    Write-Host "Please visit: http://localhost:8000" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 5: Starting server..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Start server
Set-Location "web_interface"
try {
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
} catch {
    Write-Host "ERROR: Server failed to start: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "      Service has stopped" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"