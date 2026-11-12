@echo off
setlocal enabledelayedexpansion
title Set Gallery Cube as Default Double-Click Viewer
cd /d "%~dp0"

echo ==============================================================
echo    Set Gallery Cube as Default Double-Click Viewer (Windows)
echo ==============================================================
echo.
echo This script configures Windows so double-clicking any:
echo   - HEIC / HEIF (.heic, .heif)
echo   - Photos (.jpg, .jpeg, .png, .webp, .bmp, .tiff)
echo   - Videos (.mp4, .mov)
echo will immediately open inside Gallery Cube!
echo.

set "SCRIPT_DIR=%~dp0"
set "MAIN_PY=%SCRIPT_DIR%main.py"

REM Locate Python
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%i"
    goto :found_python
)

:found_python
if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found in system PATH!
    pause
    exit /b 1
)

REM Use pythonw if available so no background black console appears
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do (
    set "PYTHON_EXE=%%i"
    goto :found_pythonw
)

:found_pythonw
echo Using Python executable: %PYTHON_EXE%
echo.

REM Register GalleryCube ProgID
reg add "HKCU\Software\Classes\GalleryCube.Media" /ve /d "Gallery Cube Media" /f >nul
reg add "HKCU\Software\Classes\GalleryCube.Media\DefaultIcon" /ve /d "%PYTHON_EXE%,0" /f >nul
reg add "HKCU\Software\Classes\GalleryCube.Media\shell\open\command" /ve /t REG_SZ /d "\"%PYTHON_EXE%\" \"%MAIN_PY%\" \"%%1\"" /f >nul

REM Associate image extensions with GalleryCube.Media
set "EXTS=.heic .heif .hif .jpg .jpeg .png .webp .bmp .tiff .mp4 .mov"

for %%e in (%EXTS%) do (
    echo Registering double-click for: %%e
    reg add "HKCU\Software\Classes\%%e" /ve /d "GalleryCube.Media" /f >nul
    reg add "HKCU\Software\Classes\%%e\OpenWithProgids" /v "GalleryCube.Media" /t REG_NONE /f >nul
)

echo.
echo ==============================================================
echo [SUCCESS] Gallery Cube is now associated with your files!
echo ==============================================================
echo Double-clicking any .heic, .jpg, .png, or .mp4 file in Windows
echo will now immediately open inside Gallery Cube!
echo.
pause

