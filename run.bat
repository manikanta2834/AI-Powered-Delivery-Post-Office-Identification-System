@echo off
setlocal enabledelayedexpansion
title AI-Powered Delivery Post Office Identification System
set "ROOT=%~dp0"
cd /d "%ROOT%"

cls
echo ====================================================================
echo   AI-POWERED DELIVERY POST OFFICE IDENTIFICATION SYSTEM
echo   Department of Posts (India Post) - Smart India Hackathon 2026
echo ====================================================================
echo.

:: Detect Python executable
if exist "%ROOT%.venv\Scripts\python.exe" (
  set "PY_EXE=%ROOT%.venv\Scripts\python.exe"
) else (
  set "PY_EXE=python"
)

:: Clean up obsolete individual bat files into unified run.bat
if exist "%ROOT%backend\scripts\cleanup_bats.py" (
  "%PY_EXE%" "%ROOT%backend\scripts\cleanup_bats.py" >nul 2>&1
)

:: -------------------------------------------------------------------
:: 1. Docker Services Check (PostgreSQL + Redis)
:: -------------------------------------------------------------------
echo [1/5] Checking Docker containers (PostgreSQL 16 + Redis 7)...
where docker >nul 2>nul
if %errorlevel% equ 0 (
  docker compose up -d >nul 2>nul
  echo [OK] Docker PostgreSQL and Redis containers active.
) else (
  echo [INFO] Docker not found. Assuming local database/redis instances.
)
echo.

:: -------------------------------------------------------------------
:: 2. Port Clearing & Kernel Socket Verification (Prevent Errno 10048)
:: -------------------------------------------------------------------
echo [2/5] Checking and clearing ports 8000, 3000, and 3001...
"%PY_EXE%" "%ROOT%backend\scripts\free_ports.py" 8000 3000 3001
echo [OK] Ports verified free to bind.
echo.

:: -------------------------------------------------------------------
:: 3. Database Collation & Redis Cache Diagnostics
:: -------------------------------------------------------------------
echo [3/5] Verifying PostgreSQL collation and Redis health...
"%PY_EXE%" -m pip install asyncpg redis kagglehub psycopg2-binary --quiet
"%PY_EXE%" "%ROOT%backend\scripts\fix_database_and_redis.py"
echo.

:: -------------------------------------------------------------------
:: 4. Postal Dataset & Datameet Maps Check / Ingestion
:: -------------------------------------------------------------------
echo [4/5] Checking postal master dataset (Kaggle PIN codes + Datameet maps)...
if "%1"=="--ingest" (
  echo   [INFO] Ingestion flag detected. Running full dataset ingestion...
  "%PY_EXE%" "%ROOT%backend\scripts\ingest_kaggle_pincodes.py"
) else (
  "%PY_EXE%" "%ROOT%backend\scripts\check_dataset_ready.py"
  if errorlevel 1 (
    echo   [INFO] Empty database detected. Running automatic one-time postal ingestion...
    "%PY_EXE%" "%ROOT%backend\scripts\ingest_kaggle_pincodes.py"
  )
)
echo.

:: -------------------------------------------------------------------
:: 5. Launch Backend & Frontend Servers
:: -------------------------------------------------------------------
echo [5/5] Launching Postal Intelligence Platform...

:: Pre-launch socket verification to guarantee port 8000 and 3000 are ready
"%PY_EXE%" "%ROOT%backend\scripts\free_ports.py" 8000 3000
timeout /t 1 >nul

:: Start FastAPI Backend
echo   - Starting FastAPI Backend on http://127.0.0.1:8000...
start "Postal Intelligence Backend API" /D "%ROOT%backend" cmd /k ""%PY_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

:: Start Next.js Frontend
echo   - Starting Next.js Frontend Web Studio on http://localhost:3000...
if not exist "%ROOT%frontend\node_modules" (
  echo   [INFO] Installing frontend dependencies...
  cd /d "%ROOT%frontend"
  call npm install
  cd /d "%ROOT%"
)
start "Postal Intelligence Web Studio" /D "%ROOT%frontend" cmd /k "npm run dev"

echo.
echo ====================================================================
echo   SUCCESS! PLATFORM IS RUNNING:
echo   ------------------------------------------------------------------
echo   Web Application: http://localhost:3000
echo   API Docs / Swagger: http://localhost:8000/docs
echo   API Health:      http://localhost:8000/api/v1/health
echo   Active Roles:    Citizen / Sorting Operator / Admin (RBAC Active)
echo ====================================================================
echo.
echo Launching default web browser in 3 seconds...
timeout /t 3 >nul
start "" "http://localhost:3000"

endlocal
