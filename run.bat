@echo off
title Gallery Cube 🧊
cd /d "%~dp0"
python main.py %*
if errorlevel 1 (
    echo.
    echo An error occurred while running Gallery Cube.
    pause
)
