@echo off
title Amazon Invoice Analyzer
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║    Amazon Invoice Analyzer               ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── Check Python ──────────────────────────────────────────────────────────────
set PYTHON_CMD=
for %%c in (python python3 py) do (
    if "!PYTHON_CMD!"=="" (
        %%c --version >nul 2>&1 && set PYTHON_CMD=%%c
    )
)

if "!PYTHON_CMD!"=="" (
    echo [ERREUR] Python 3 introuvable.
    echo Installez-le depuis https://www.python.org/downloads/
    echo Cochez bien "Add Python to PATH" lors de l'installation.
    pause & exit /b 1
)
echo [OK] Python detecte : !PYTHON_CMD!

:: ── Check Node ────────────────────────────────────────────────────────────────
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Node.js introuvable.
    echo Installez-le depuis https://nodejs.org/  (version LTS recommandee^)
    pause & exit /b 1
)
echo [OK] Node.js detecte

:: ── Install backend dependencies ─────────────────────────────────────────────
echo.
echo [1/4] Installation des dependances Python...
cd backend
!PYTHON_CMD! -m pip install -r requirements.txt -q
!PYTHON_CMD! -m playwright install chromium 2>nul || !PYTHON_CMD! -m playwright install chromium
cd ..

:: ── Start backend ─────────────────────────────────────────────────────────────
echo [2/4] Demarrage du backend (port 8000)...
start "AIA-Backend" /B cmd /c "cd /d "%~dp0backend" && !PYTHON_CMD! -m uvicorn main:app --reload --port 8000"

:: ── Install & start frontend ──────────────────────────────────────────────────
echo [3/4] Installation des dependances Node.js...
cd frontend
call npm install --silent
echo [4/4] Demarrage du frontend (port 5173)...
start "AIA-Frontend" /B cmd /c "cd /d "%~dp0frontend" && npm run dev"
cd ..

:: ── Open browser ──────────────────────────────────────────────────────────────
timeout /t 4 /nobreak >nul
start http://localhost:5173

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  Application prête sur localhost:5173    ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Fermez cette fenetre pour arreter l'application.
echo.
pause >nul

taskkill /fi "WINDOWTITLE eq AIA-Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq AIA-Frontend*" /f >nul 2>&1
