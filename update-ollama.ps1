# Download Ollama update via PowerShell with proxy support
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

$url = "https://github.com/ollama/ollama/releases/download/v0.20.2/ollama-windows-amd64.zip"
$dest = "$env:USERPROFILE\Downloads\ollama-windows-amd64.zip"

Write-Host "Downloading Ollama v0.20.2..."
$client = New-Object System.Net.WebClient
try {
    $client.DownloadFile($url, $dest)
    Write-Host "Download complete: $dest"
    $size = (Get-Item $dest).Length / 1MB
    Write-Host "File size: $([math]::Round($size, 2)) MB"
} catch {
    Write-Host "Download failed: $_"
}
