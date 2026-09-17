@echo off
title Clean Up Stray Folders
echo ============================================================
echo   Cleaning up accidental stray empty folders
echo ============================================================
cd /d "%~dp0"

for /d %%i in ("C*UsersKirito*") do (
    echo Removing: %%i
    rd /s /q "%%i"
)

if exist "UsersKiritoOneDriveDesktop2.5.1web-ui" (
    echo Removing: UsersKiritoOneDriveDesktop2.5.1web-ui
    rd /s /q "UsersKiritoOneDriveDesktop2.5.1web-ui"
)

echo.
echo Clean-up complete! Only genuine project code (src, web-ui, fovea_lidar) remains.
echo You can close this window now.
pause
