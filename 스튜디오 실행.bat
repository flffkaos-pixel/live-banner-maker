@echo off
cd /d "%~dp0"
echo Starting Live Banner Studio...
echo.

powershell -NoProfile -Command "try{ (Invoke-WebRequest 'http://127.0.0.1:8090/index.html' -UseBasicParsing -TimeoutSec 2) | Out-Null; exit 0 }catch{ exit 1 }"
if %errorlevel%==0 goto openwindow

echo Starting server (do NOT close this window)...
start "" /min python serve.py

powershell -NoProfile -Command "for($i=0;$i -lt 20;$i++){ try{ (Invoke-WebRequest 'http://127.0.0.1:8090/index.html' -UseBasicParsing -TimeoutSec 1) | Out-Null; exit 0 }catch{ Start-Sleep -Milliseconds 500 } }; exit 1"

:openwindow
start "" "http://127.0.0.1:8090/index.html?v=19"
echo.
echo Studio opened in your browser.
ping -n 3 127.0.0.1 >nul
