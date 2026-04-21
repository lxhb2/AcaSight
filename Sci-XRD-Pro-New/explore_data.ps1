Get-ChildItem "G:\Program Files (x86)\ICDD PDF-4+ 2009\Data" -Recurse | 
Where-Object { -not $_.PSIsContainer } | 
Select-Object FullName, Length, Extension | 
Format-Table -AutoSize
