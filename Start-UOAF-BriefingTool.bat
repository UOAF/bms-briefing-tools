@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Local virtual environment not found. Running installer first...
  call "%~dp0Install-UOAF-BriefingTool.bat"
)
".venv\Scripts\python.exe" "scripts\launch_local_app.py"
