@echo off
setlocal enabledelayedexpansion
title Gallery Cube - Windows Explorer Integration
cd /d "%~dp0"

echo ==============================================================
echo        Gallery Cube - Windows Explorer Integration Setup
echo ==============================================================
echo.
echo 1. Register "Edit in Gallery Cube" Right-Click Context Menu
echo 2. Enable Windows File Explorer Preview Pane & Thumbnails Guide
echo.

set "SCRIPT_DIR=%~dp0"
set "MAIN_PY=%SCRIPT_DIR%main.py"

REM Get python path
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%i"
    goto :found_python
)

:found_python
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found in PATH!
    pause
    exit /b 1
)

echo Found Python: %PYTHON_EXE%
echo Main Script: %MAIN_PY%
echo.

echo Adding Right-Click Menu for all image formats in Windows Explorer...

REM Add to SystemFileAssociations\image
reg add "HKCU\Software\Classes\SystemFileAssociations\image\shell\GalleryCube" /ve /d "Edit in Gallery Cube 🧊" /f >nul
reg add "HKCU\Software\Classes\SystemFileAssociations\image\shell\GalleryCube" /v "Icon" /t REG_SZ /d "%PYTHON_EXE%,0" /f >nul
reg add "HKCU\Software\Classes\SystemFileAssociations\image\shell\GalleryCube\command" /ve /t REG_SZ /d "\"%PYTHON_EXE%\" \"%MAIN_PY%\" \"%%1\"" /f >nul

REM Specific .heic and .heif association
reg add "HKCU\Software\Classes\.heic\OpenWithProgids" /v "GalleryCube.heic" /t REG_NONE /f >nul
reg add "HKCU\Software\Classes\GalleryCube.heic" /ve /d "HEIC Flagship Image" /f >nul
reg add "HKCU\Software\Classes\GalleryCube.heic\shell\open\command" /ve /t REG_SZ /d "\"%PYTHON_EXE%\" \"%MAIN_PY%\" \"%%1\"" /f >nul

echo [OK] Right-click context menu "Edit in Gallery Cube" successfully registered!
echo.
echo ==============================================================
echo    HOW TO SHOW HEIC PREVIEWS IN WINDOWS EXPLORER PREVIEW PANE:
echo ==============================================================
echo Windows File Explorer requires a 64-bit COM Preview Handler
echo to render HEIC in the Explorer Preview Pane (Alt+P).
echo.
echo Recommended 100%% Free Solutions for Windows Explorer Preview:
echo.
echo [Option A] CopyTrans HEIC for Windows (Most popular free shell previewer)
echo     Download free installer from: https://www.copytrans.net/copytransheic/
echo     - Once installed, Windows File Explorer will instantly render
echo       HEIC thumbnails and the right-hand Preview Pane (Alt+P).
echo.
echo [Option B] QuickLook (Free on GitHub / Microsoft Store)
echo     - Allows you to select ANY .heic file in Windows Explorer and press
echo       the [SPACEBAR] for an instant large fluid preview!
echo.
echo [Option C] Gallery Cube Built-In Preview Mode
echo     - Open Gallery Cube, click 'Open Folder', and switch to the
echo       'Folder & Thumbnails' tab to preview any album with zero setup!
echo.
pause

