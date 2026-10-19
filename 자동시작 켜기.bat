@echo off
echo Registering Live Banner Studio auto-start...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0autostart_on.ps1"
echo.
echo Done. Studio will start automatically at Windows logon.
pause
