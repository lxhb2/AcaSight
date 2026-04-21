Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$imgPath = "C:\Users\Administrator\.qclaw\media\inbound\4f5c20a8-a58c-4521-8659-81d777ebce72.jpg"
$bmp = [System.Drawing.Image]::FromFile($imgPath)
$frm = [System.Drawing.Image]::FromFile($imgPath)
Write-Host "Width: $($frm.Width), Height: $($frm.Height)"
Write-Host "PixelFormat: $($frm.PixelFormat)"
$frm.Dispose()
$bmp.Dispose()
Write-Host "Done"
