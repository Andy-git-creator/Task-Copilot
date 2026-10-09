@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. See README.md.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Frontend build is missing. Run npm install and npm run build in frontend.
  pause
  exit /b 1
)
set "TASK_COPILOT_DATA_DIR=%~dp0.local-data"
if not exist ".local-data" mkdir ".local-data"
start "" ".venv\Scripts\pythonw.exe" start.pyw
