# Remove Live Banner Studio auto-start
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'LiveBannerStudio.lnk'
if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host "Removed -> $lnk" }
else { Write-Host "Not registered." }
