@echo off
setlocal enabledelayedexpansion
title Push 2.5D-Lidar to GitHub
cd /d "%~dp0"

echo ==============================================================================
echo    2.5D FOVEATED LIDAR - GITHUB COMMIT AND PUSH UTILITY
echo ==============================================================================
echo.

:: 1. Locate Git executable
set "GIT_CMD=git"
where git >nul 2>nul
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Git\cmd\git.exe" (
        set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
    ) else if exist "C:\Program Files\Git\bin\git.exe" (
        set "GIT_CMD=C:\Program Files\Git\bin\git.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
    ) else (
        echo [ERROR] Git was not found on your system!
        echo Please install Git from https://git-scm.com/ and try again.
        pause
        exit /b 1
    )
)

echo [INFO] Using Git: "%GIT_CMD%"
echo.

:: 2. Initialize Git if needed
if not exist ".git" (
    echo [INFO] Initializing Git repository...
    "%GIT_CMD%" init
) else (
    echo [INFO] Existing Git repository detected.
)
echo.

:: 3. Configure Remote URL
set "REMOTE_URL=git@github.com:Kadhare-Raj-Chandrakant/2.5D-Lidar.git"
"%GIT_CMD%" remote get-url origin >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Updating remote origin to: %REMOTE_URL%
    "%GIT_CMD%" remote set-url origin %REMOTE_URL%
) else (
    echo [INFO] Setting remote origin to: %REMOTE_URL%
    "%GIT_CMD%" remote add origin %REMOTE_URL%
)
echo.

:: 4. Verify branch name
"%GIT_CMD%" branch -M main

:: 5. Synchronize presentation assets & stage files
if exist "copy_assets.bat" call copy_assets.bat
echo.
echo [INFO] Staging files (respecting .gitignore)...
"%GIT_CMD%" add .

echo.
echo [INFO] Staged files summary:
"%GIT_CMD%" status --short
echo.

:: 6. Commit changes
echo [INFO] Creating commit...
"%GIT_CMD%" commit -m "feat: complete 2.5D foveated lidar perception pipeline, PointNet semantic segmentation, and real-time 3D web simulation"
if %errorlevel% neq 0 (
    echo [INFO] No new changes to commit or commit already up to date.
)
echo.

:: 7. Push to GitHub
echo ==============================================================================
echo [INFO] Pushing to GitHub (%REMOTE_URL% on branch 'main')...
echo ==============================================================================
"%GIT_CMD%" push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo ==============================================================================
    echo [NOTICE] If the SSH push failed above (e.g. Permission denied / publickey):
    echo.
    echo Option A (SSH): Ensure your SSH key is added to GitHub:
    echo                 ssh-add ~/.ssh/id_rsa   or   ssh-add ~/.ssh/id_ed25519
    echo.
    echo Option B (HTTPS): Switch to HTTPS and personal access token:
    echo                 git remote set-url origin https://github.com/Kadhare-Raj-Chandrakant/2.5D-Lidar.git
    echo                 git push -u origin main
    echo ==============================================================================
) else (
    echo.
    echo ==============================================================================
    echo [SUCCESS] Project successfully pushed to GitHub!
    echo URL: https://github.com/Kadhare-Raj-Chandrakant/2.5D-Lidar
    echo ==============================================================================
)

echo.
pause
