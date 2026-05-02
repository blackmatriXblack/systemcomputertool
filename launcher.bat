@echo off
title ComputerTool - System Tools Launcher
echo.
echo   Starting ComputerTool...
echo.

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python is not installed or not in PATH.
    echo   Please install Python 3.7+ from https://python.org
    echo   Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Run ComputerTool
cd /d "%~dp0"
python computertool.py %*

if %errorlevel% neq 0 (
    echo.
    echo   Press any key to exit...
    pause >nul
)
