@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment missing. Running setup...
  call setup.bat
  if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Setup did not create .venv
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -c "import aiohttp, pystray, PIL, webview" 2>nul
if errorlevel 1 (
  echo Dependencies missing or broken. Re-running setup...
  call setup.bat
)

echo Starting Velo...
".venv\Scripts\python.exe" main.py
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo Velo exited with code %ERR%.
  echo If the port is in use, open Settings and change Port, or close the other app.
  echo.
  pause
)
exit /b %ERR%
