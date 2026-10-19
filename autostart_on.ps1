# Register Live Banner Studio to auto-start at Windows logon
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs  = Join-Path $base 'auto-start.vbs'
$lnk  = Join-Path ([Environment]::GetFolderPath('Startup')) 'LiveBannerStudio.lnk'
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"' + $vbs + '"'
$s.WorkingDirectory = $base
$s.WindowStyle = 7
$s.Description = 'Live Banner Studio auto-start'
$s.Save()
Write-Host "OK -> $lnk"
