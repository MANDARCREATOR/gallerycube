@echo off
title Build Minimized Gallery Cube .EXE
cd /d "%~dp0"

echo ==============================================================
echo        Building Optimized Lightweight Gallery Cube .EXE
echo ==============================================================
echo.

REM Check if pyinstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [INFO] PyInstaller not detected. Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo [1/2] Compiling with optimized exclusion spec (stripping unused frameworks)...
pyinstaller --clean -y gallery_cube.spec

if errorlevel 1 (
    echo [ERROR] Build failed! Check terminal logs above.
    pause
    exit /b 1
)

echo.
echo [2/2] Build Successful!
echo ==============================================================
echo  Executable created at:
echo  %~dp0dist\GalleryCube.exe
echo ==============================================================
echo.
pause

