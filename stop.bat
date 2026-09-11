@echo off
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

echo Terminating any active processes on ports 8000, 3000, and 3001...
if exist "%ROOT%.venv\Scripts\python.exe" (
  "%ROOT%.venv\Scripts\python.exe" "%ROOT%backend\scripts\free_ports.py" 8000 3000 3001
) else (
  python "%ROOT%backend\scripts\free_ports.py" 8000 3000 3001
)

echo [OK] Ports 8000, 3000, and 3001 are completely released.
endlocal
