@echo off
:: Amazon Invoice Analyzer — Smart Installer & Launcher (Windows)
:: • Scanne Python 3.10+ et Node.js 18+, installe via winget si absents
:: • 1er lancement : sélecteur de dossier graphique, copie, dépendances, raccourci Bureau
:: • Lancements suivants : démarre directement l'application

chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title Amazon Invoice Analyzer

set "CONFIG_DIR=%APPDATA%\amazon-analyzer"
set "CONFIG=%CONFIG_DIR%\install_path.txt"
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"

cls
echo.
echo   =================================================
echo    📦  Amazon Invoice Analyzer
echo   =================================================
echo.

:: ═══════════════════════════════════════════════════════════════════════════
:: 1. PYTHON 3.10+
:: ═══════════════════════════════════════════════════════════════════════════
echo   [1/4] Verification de Python 3.10+...

set "PYTHON_CMD="
for %%c in (python python3 py) do (
    if "!PYTHON_CMD!"=="" (
        %%c --version >nul 2>&1
        if not errorlevel 1 (
            :: Check version >= 3.10
            for /f "tokens=2 delims= " %%v in ('%%c --version 2^>^&1') do (
                for /f "tokens=1,2 delims=." %%a in ("%%v") do (
                    set /a "ver_check=%%a*100+%%b"
                    if !ver_check! GEQ 310 set "PYTHON_CMD=%%c"
                )
            )
        )
    )
)

if "!PYTHON_CMD!"=="" (
    echo   [!] Python 3.10+ introuvable. Installation automatique...

    :: Try winget first (Windows 10 1809+ / Windows 11)
    winget --version >nul 2>&1
    if not errorlevel 1 (
        echo   Lancement de winget install Python...
        winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        :: Refresh PATH
        for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "HKCU_PATH=%%a %%b"
        set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts"
        set "PATH=%PATH%;%APPDATA%\Python\Python312\Scripts"
        :: Re-check
        for %%c in (python python3 py) do (
            if "!PYTHON_CMD!"=="" (
                %%c --version >nul 2>&1
                if not errorlevel 1 set "PYTHON_CMD=%%c"
            )
        )
    )

    if "!PYTHON_CMD!"=="" (
        echo   Installation automatique impossible.
        echo   Installez Python 3.10+ depuis : https://www.python.org/downloads/
        start https://www.python.org/downloads/
        echo.
        echo   Cochez bien "Add Python to PATH" lors de l'installation !
        pause
        :: Re-check after manual install
        for %%c in (python python3 py) do (
            if "!PYTHON_CMD!"=="" (
                %%c --version >nul 2>&1
                if not errorlevel 1 set "PYTHON_CMD=%%c"
            )
        )
        if "!PYTHON_CMD!"=="" ( echo   ERREUR : Python introuvable. Arret. & pause & exit /b 1 )
    )
)

for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do echo   [OK] %%v

:: ═══════════════════════════════════════════════════════════════════════════
:: 2. NODE.JS 18+
:: ═══════════════════════════════════════════════════════════════════════════
echo   [2/4] Verification de Node.js 18+...

set "NODE_OK=0"
node --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=1 delims=." %%v in ('node --version') do (
        set "node_major=%%v"
        set "node_major=!node_major:v=!"
        if !node_major! GEQ 18 set "NODE_OK=1"
    )
)

if "!NODE_OK!"=="0" (
    echo   [!] Node.js 18+ introuvable. Installation automatique...

    winget --version >nul 2>&1
    if not errorlevel 1 (
        winget install --id OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements
        :: Refresh PATH with common Node install locations
        set "PATH=%PATH%;%ProgramFiles%\nodejs;%APPDATA%\npm"
        node --version >nul 2>&1 && set "NODE_OK=1"
    )

    if "!NODE_OK!"=="0" (
        echo   Installation automatique impossible.
        echo   Installez Node.js 18+ depuis : https://nodejs.org/downloads/
        start https://nodejs.org/downloads/
        pause
        node --version >nul 2>&1 && set "NODE_OK=1"
        if "!NODE_OK!"=="0" ( echo   ERREUR : Node.js introuvable. Arret. & pause & exit /b 1 )
    )
)

for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo   [OK] Node.js %%v

:: ═══════════════════════════════════════════════════════════════════════════
:: 3. PREMIERE INSTALLATION
:: ═══════════════════════════════════════════════════════════════════════════
set "INSTALL_DIR="
if exist "%CONFIG%" (
    set /p INSTALL_DIR=<"%CONFIG%"
    if not exist "!INSTALL_DIR!" set "INSTALL_DIR="
)

if "!INSTALL_DIR!"=="" (
    echo.
    echo   [3/4] Premiere installation — choisissez le dossier de destination...
    echo.

    :: Folder picker via PowerShell
    for /f "delims=" %%F in ('powershell -NoProfile -Command ^
        "Add-Type -AssemblyName System.Windows.Forms; ^
         $d = New-Object System.Windows.Forms.FolderBrowserDialog; ^
         $d.Description = 'Choisissez ou installer Amazon Invoice Analyzer'; ^
         $d.RootFolder = 'MyComputer'; ^
         $d.ShowNewFolderButton = $true; ^
         [void]$d.ShowDialog(); ^
         $d.SelectedPath"') do set "CHOSEN=%%F"

    if "!CHOSEN!"=="" set "CHOSEN=%USERPROFILE%"
    set "INSTALL_DIR=!CHOSEN!\Amazon Invoice Analyzer"

    echo   Dossier choisi : !INSTALL_DIR!
    mkdir "!INSTALL_DIR!" 2>nul

    :: Copy files (robocopy excludes build artifacts)
    echo   Copie des fichiers...
    robocopy "%SRC%" "!INSTALL_DIR!" /E /XD node_modules __pycache__ .git .claude docs /XF *.pyc /NFL /NDL /NJH /NJS >nul
    echo   [OK] Fichiers copies

    :: Install Python deps
    echo   Installation des dependances Python...
    cd /d "!INSTALL_DIR!\backend"
    !PYTHON_CMD! -m pip install -r requirements.txt -q
    !PYTHON_CMD! -m playwright install chromium
    echo   [OK] Dependances Python

    :: Install Node deps
    echo   Installation des dependances Node.js...
    cd /d "!INSTALL_DIR!\frontend"
    call npm install --silent
    echo   [OK] Dependances Node.js

    :: Desktop shortcut via PowerShell
    powershell -NoProfile -Command ^
        "$ws = New-Object -ComObject WScript.Shell; ^
         $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Amazon Analyzer.lnk'); ^
         $s.TargetPath = '!INSTALL_DIR!\start.bat'; ^
         $s.WorkingDirectory = '!INSTALL_DIR!'; ^
         $s.IconLocation = 'shell32.dll,258'; ^
         $s.Description = 'Amazon Invoice Analyzer'; ^
         $s.Save()"
    echo   [OK] Raccourci cree sur le Bureau

    :: Save config
    if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
    echo !INSTALL_DIR!>"%CONFIG%"

    echo.
    echo   =================================================
    echo    [OK] Installation terminee !
    echo    - Raccourci : Bureau → Amazon Analyzer
    echo   =================================================
    echo.
    timeout /t 2 /nobreak >nul
) else (
    echo   [3/4] Installation existante trouvee : !INSTALL_DIR!
)

:: ═══════════════════════════════════════════════════════════════════════════
:: 4. LANCEMENT
:: ═══════════════════════════════════════════════════════════════════════════
echo   [4/4] Lancement de l'application...

:: Check if already running on port 8000 + 5173
netstat -ano | find ":8000" | find "LISTENING" >nul 2>&1
set "BACK_RUNNING=!errorlevel!"
netstat -ano | find ":5173" | find "LISTENING" >nul 2>&1
set "FRONT_RUNNING=!errorlevel!"

if "!BACK_RUNNING!"=="0" if "!FRONT_RUNNING!"=="0" (
    echo   [OK] Application deja en cours — ouverture du navigateur...
    start http://localhost:5173
    exit /b 0
)

cd /d "!INSTALL_DIR!\backend"
start "AIA-Backend" /B cmd /c "!PYTHON_CMD! -m uvicorn main:app --reload --port 8000 2>&1"

cd /d "!INSTALL_DIR!\frontend"
start "AIA-Frontend" /B cmd /c "npm run dev 2>&1"

timeout /t 4 /nobreak >nul
start http://localhost:5173

echo.
echo   =================================================
echo    Application disponible sur localhost:5173
echo    Fermez cette fenetre pour arreter.
echo   =================================================
echo.
pause >nul

taskkill /fi "WINDOWTITLE eq AIA-Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq AIA-Frontend*" /f >nul 2>&1
