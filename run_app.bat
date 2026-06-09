@echo off
title DR80 Theoretical Price Calculator
cd /d "%~dp0"
echo Starting DR80 Theoretical Price Calculator...
python dr80_calculator.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to launch. Make sure Python and dependencies are installed.
    echo Run: pip install -r requirements.txt
    pause
)
