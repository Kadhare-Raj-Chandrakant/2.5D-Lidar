@echo off
title AV Python Backend
cd /d "%~dp0"
echo ============================================================
echo   Starting Autonomous Vehicle Simulation Backend (Python)
echo ============================================================
python main.py --headless
pause
