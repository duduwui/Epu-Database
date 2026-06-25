@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\Program Files\PostgreSQL\17\bin;%PATH%"

:: Enable Flask Debug Mode for Auto-Reloading
set FLASK_DEBUG=true
set TEMPLATES_AUTO_RELOAD=true

echo Starting EPU MIS in AUTO-RELOAD (Debug) mode...
echo Do not close this window. When you save a file, the server will restart automatically!
echo ======================================================================================
".venv\Scripts\python.exe" app.py
pause
