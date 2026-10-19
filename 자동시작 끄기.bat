@echo off
echo Removing Live Banner Studio auto-start...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0autostart_off.ps1"
echo.
pause
