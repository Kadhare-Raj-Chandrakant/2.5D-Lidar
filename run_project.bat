@echo off
title Autonomous Vehicle Simulation Launcher
echo ============================================================
echo   Starting Autonomous Vehicle 3D Simulation System
echo ============================================================

echo Cleaning up any stray temporary folders...
for /d %%i in ("%~dp0C*UsersKirito*") do rd /s /q "%%i" 2>nul
if exist "%~dp0UsersKiritoOneDriveDesktop2.5.1web-ui" rd /s /q "%~dp0UsersKiritoOneDriveDesktop2.5.1web-ui" 2>nul

echo [1/2] Launching Python Simulation Backend (ws://localhost:8765)...
start "AV Backend (Python)" cmd /k "cd /d "%~dp0" && python main.py --headless"

echo [2/2] Launching 3D Web UI Frontend (http://localhost:3000)...
start "AV Web UI (Vite)" cmd /k "cd /d "%~dp0web-ui" && npm run dev"

echo.
echo Waiting for Vite server to start up...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo Simulation active! Both terminal windows will remain open.
pause
