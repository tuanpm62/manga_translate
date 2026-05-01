@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Manga Translate

:: ── resolve the directory this .bat lives in ─────────────────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

:: ── locate %MT% (PATH first, then Python Scripts fallback) ────────
set "MT=manga-translate"
set "MT_READY=0"
where %MT% >nul 2>&1
if not errorlevel 1 (
    set "MT_READY=1"
) else (
    :: ask Python where its Scripts folder is
    for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))" 2^>nul') do set "PY_SCRIPTS=%%i"
    if defined PY_SCRIPTS (
        if exist "!PY_SCRIPTS!\manga-translate.exe" (
            set "MT=!PY_SCRIPTS!\manga-translate.exe"
            set "MT_READY=1"
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

:: ── [I] Install ───────────────────────────────────────────────────────────
:INSTALL
cls
echo  [Install / update dependencies]
echo.
pip install -e "%ROOT%"
pip install websockets pyperclip
echo.

:: ── add Python Scripts to PATH for this session ───────────────────────────
for /f "delims=" %%i in ('python -c "import sysconfig; print(sysconfig.get_path(\"scripts\"))"') do set "PY_SCRIPTS=%%i"
if defined PY_SCRIPTS (
    set "PATH=%PY_SCRIPTS%;%PATH%"
    echo  Added to PATH (this session): %PY_SCRIPTS%
)

:: ── re-check ──────────────────────────────────────────────────────────────
set "MT_READY=1"
where %MT% >nul 2>&1
if errorlevel 1 (
    set "MT_READY=0"
    echo  [!] %MT% still not found.
    echo      Add the Python Scripts folder to your system PATH permanently,
    echo      or run this launcher from the same terminal where pip installed it.
) else (
    echo  [OK] %MT% is ready.
)
echo.
pause
goto :MENU
