@echo off
title AV Web UI Server
cd /d "%~dp0web-ui"
echo ============================================================
echo   Starting Autonomous Vehicle Web UI Server (Vite)
echo ============================================================
npm run dev
pause
