@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\Install-UOAF-BriefingTool.ps1"
if errorlevel 1 (
  echo.
  echo Install failed. See the messages above.
  pause
  exit /b 1
)
echo.
echo Install complete.
pause
