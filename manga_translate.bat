@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Manga Translate

:: ── resolve the directory this .bat lives in ─────────────────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

:: ── locate %MT%: venv first, then PATH, then Python Scripts fallback ──
set "MT=manga-translate"
set "MT_READY=0"
if exist "%ROOT%\.venv\Scripts\manga-translate.exe" (
    set "MT=%ROOT%\.venv\Scripts\manga-translate.exe"
    set "MT_READY=1"
) else (
    where manga-translate >nul 2>&1
    if not errorlevel 1 (
        set "MT_READY=1"
    ) else (
        for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))" 2^>nul') do set "PY_SCRIPTS=%%i"
        if defined PY_SCRIPTS (
            if exist "!PY_SCRIPTS!\manga-translate.exe" (
                set "MT=!PY_SCRIPTS!\manga-translate.exe"
                set "MT_READY=1"
            )
        )
    )
)

:MENU
cls
echo.
echo  ============================================================
echo    MANGA TRANSLATE  ^|  manga_ocr + translation
echo  ============================================================
echo.
if "%MT_READY%"=="0" (
    echo  [!] %MT% is not installed yet.
    echo      Choose [I] to install, then reopen this launcher.
    echo.
)
echo   Modes
echo   -----
echo   [1]  Clipboard watch    ^|  auto-translate every clipboard image
echo   [2]  Screenshot / snip  ^|  draw a region on screen
echo   [3]  Folder watch       ^|  monitor a folder for new images
echo   [4]  Translate file     ^|  single image file
echo   [5]  Batch translate    ^|  all images in a folder ^(one-shot^)
echo   [6]  WebSocket server   ^|  ws://localhost:7331
echo.
echo   Config
echo   ------
echo   [C]  Edit config        ^|  change service, API key, languages...
echo   [S]  Show config        ^|  display current settings
echo   [R]  Reset config       ^|  restore defaults
echo.
echo   Setup
echo   -----
echo   [I]  Install / update   ^|  pip install -e .
echo   [Q]  Quit
echo.
set /p "CHOICE=  Select: "
echo.

if /i "%CHOICE%"=="i" goto :INSTALL
if /i "%CHOICE%"=="q" goto :EOF

if "%MT_READY%"=="0" (
    echo.
    echo  [!] Please install first — choose [I].
    echo.
    pause
    goto :MENU
)

if /i "%CHOICE%"=="1" goto :WATCH
if /i "%CHOICE%"=="2" goto :SCREENSHOT
if /i "%CHOICE%"=="3" goto :FOLDER
if /i "%CHOICE%"=="4" goto :FILE
if /i "%CHOICE%"=="5" goto :BATCH
if /i "%CHOICE%"=="6" goto :SERVE
if /i "%CHOICE%"=="c" goto :EDIT_CONFIG
if /i "%CHOICE%"=="s" goto :SHOW_CONFIG
if /i "%CHOICE%"=="r" goto :RESET_CONFIG
goto :MENU

:: ── [1] Clipboard watch ───────────────────────────────────────────────────
:WATCH
cls
echo  [Clipboard watch]  Ctrl+C to stop.
echo.
set "EXTRA="
set /p "WRITETO=  Write to (clipboard / path to .txt) [Enter = clipboard]: "
if not "%WRITETO%"=="" set "EXTRA=--write-to "%WRITETO%""
%MT% watch %EXTRA%
echo.
pause
goto :MENU

:: ── [2] Screenshot ────────────────────────────────────────────────────────
:SCREENSHOT
cls
echo  [Screenshot]
echo.
set "EXTRA="
set /p "OUTIMG=  Save overlaid image to (leave blank to skip): "
if not "%OUTIMG%"=="" set "EXTRA=--output "%OUTIMG%""
set /p "WRITETO=  Write to (clipboard / path to .txt) [Enter = clipboard]: "
if not "%WRITETO%"=="" set "EXTRA=%EXTRA% --write-to "%WRITETO%""
%MT% screenshot %EXTRA%
echo.
pause
goto :MENU

:: ── [3] Folder watch ──────────────────────────────────────────────────────
:FOLDER
cls
echo  [Folder watch]  Ctrl+C to stop.
echo.
set /p "DIR=  Folder to watch: "
if "%DIR%"=="" goto :MENU
set "EXTRA="
set /p "WRITETO=  Write to (clipboard / path to .txt) [Enter = clipboard]: "
if not "%WRITETO%"=="" set "EXTRA=--write-to "%WRITETO%""
%MT% folder "%DIR%" %EXTRA%
echo.
pause
goto :MENU

:: ── [4] Translate single file ─────────────────────────────────────────────
:FILE
cls
echo  [Translate file]
echo.
set /p "IMGPATH=  Image path: "
if "%IMGPATH%"=="" goto :MENU
set "EXTRA="
set /p "OUTIMG=  Save overlaid image to (leave blank to skip): "
if not "%OUTIMG%"=="" set "EXTRA=--output "%OUTIMG%""
set /p "WRITETO=  Write to (clipboard / path to .txt) [Enter = clipboard]: "
if not "%WRITETO%"=="" set "EXTRA=%EXTRA% --write-to "%WRITETO%""
%MT% translate "%IMGPATH%" %EXTRA%
echo.
pause
goto :MENU

:: ── [5] Batch translate ───────────────────────────────────────────────────
:BATCH
cls
echo  [Batch translate]
echo.
set /p "DIRPATH=  Folder with images: "
if "%DIRPATH%"=="" goto :MENU
set "EXTRA="
set /p "OUTDIR=  Output folder for overlaid images (leave blank to skip): "
if not "%OUTDIR%"=="" set "EXTRA=--output-dir "%OUTDIR%""
%MT% batch "%DIRPATH%" %EXTRA%
echo.
pause
goto :MENU

:: ── [6] WebSocket server ──────────────────────────────────────────────────
:SERVE
cls
echo  [WebSocket server]  Ctrl+C to stop.
echo.
set "EXTRA="
set /p "HOST=  Host [Enter = localhost]: "
if not "%HOST%"=="" set "EXTRA=--host "%HOST%""
set /p "PORT=  Port [Enter = 7331]: "
if not "%PORT%"=="" set "EXTRA=%EXTRA% --port %PORT%"
%MT% serve %EXTRA%
echo.
pause
goto :MENU

:: ── [C] Edit config ───────────────────────────────────────────────────────
:EDIT_CONFIG
cls
echo  [Edit config]  Opening config file in Notepad...
echo.
echo  Common keys:
echo    service       google ^| deepl
echo    api_key       your DeepL API key ^(or leave null for Google^)
echo    use_free_api  true = DeepL Free   false = DeepL Pro
echo    source_lang   ja  ^(Japanese^)
echo    target_lang   en  ^(English^)
echo    model         kha-white/manga-ocr-base
echo    force_cpu     false
echo    delay_secs    0.1
echo    write_to      clipboard ^| path/to/output.txt
echo    verbose       false
echo.
%MT% config --edit
echo.
pause
goto :MENU

:: ── [S] Show config ───────────────────────────────────────────────────────
:SHOW_CONFIG
cls
echo  [Current config]
echo.
%MT% config --show
echo.
pause
goto :MENU

:: ── [R] Reset config ──────────────────────────────────────────────────────
:RESET_CONFIG
cls
echo  [Reset config]
echo.
%MT% config --reset
echo.
pause
goto :MENU

:: ── [I] Install / update — smart flow ────────────────────────────────────
:INSTALL
cls
echo  [Install / update — checking requirements]
echo.

:: ── Step 1: Virtual environment ───────────────────────────────────────────
echo  [1/2] Virtual environment
if exist "%ROOT%\.venv\Scripts\python.exe" (
    echo        [OK] .venv already exists — will use it.
    set "USE_VENV=1"
) else (
    echo        [--] No .venv found.
    set /p "CREATEVENV=        Create virtual environment? [Y/n] "
    if /i "!CREATEVENV!"=="n" (
        set "USE_VENV=0"
        echo        Using current Python environment.
    ) else (
        echo        Creating %ROOT%\.venv ...
        python -m venv "%ROOT%\.venv"
        set "USE_VENV=1"
        echo        [OK] Created.
    )
)
echo.

:: ── Step 2: Install package ───────────────────────────────────────────────
echo  [2/2] Package ^(manga_translate^)
if "!USE_VENV!"=="1" (
    set "INST_PIP=%ROOT%\.venv\Scripts\pip.exe"
    "!INST_PIP!" install --upgrade pip --quiet
) else (
    set "INST_PIP=pip"
)
"!INST_PIP!" install -e "%ROOT%"
echo        [OK] manga_translate installed/updated.
echo.

:: ── Refresh MT path ───────────────────────────────────────────────────────
if "!USE_VENV!"=="1" (
    if exist "%ROOT%\.venv\Scripts\manga-translate.exe" (
        set "MT=%ROOT%\.venv\Scripts\manga-translate.exe"
        set "MT_READY=1"
        echo  [OK] manga-translate is ready ^(venv^).
    ) else (
        set "MT_READY=0"
        echo  [!] manga-translate not found in .venv\Scripts — pip install may have failed.
    )
) else (
    for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set "PY_SCRIPTS=%%i"
    if defined PY_SCRIPTS set "PATH=!PY_SCRIPTS!;%PATH%"
    where manga-translate >nul 2>&1
    if not errorlevel 1 (
        set "MT_READY=1"
        echo  [OK] manga-translate is ready.
    ) else (
        set "MT_READY=0"
        echo  [!] manga-translate not found — add Python Scripts to PATH.
    )
)
echo.
pause
goto :MENU
