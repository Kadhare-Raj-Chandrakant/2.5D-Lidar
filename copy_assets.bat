@echo off
setlocal
cd /d "%~dp0"

echo [INFO] Synchronizing presentation assets into assets/ directory...
if not exist "assets" mkdir "assets"

set "BRAIN_DIR=C:\Users\Kirito\.gemini\antigravity-ide\brain\a54a4800-d5f1-46bc-877e-46319505b960"

:: 1. 3D Environment UI with Pedestrians & Cockpit HUD
if exist "%BRAIN_DIR%\environment_ui_pedestrian_1789687031854.jpg" (
    copy /y "%BRAIN_DIR%\environment_ui_pedestrian_1789687031854.jpg" "assets\environment_ui_pedestrians.jpg" >nul
    echo  [+] Copied assets\environment_ui_pedestrians.jpg
)

:: 2. Isometric 3D Foveated Grid CAD / WebGL Inspection View
if exist "%BRAIN_DIR%\foveated_grid_3d_inspection_1789687047746.jpg" (
    copy /y "%BRAIN_DIR%\foveated_grid_3d_inspection_1789687047746.jpg" "assets\foveated_grid_3d_inspection.jpg" >nul
    echo  [+] Copied assets\foveated_grid_3d_inspection.jpg
)

:: 3. Web UI Dashboard Capture
if exist "%BRAIN_DIR%\.user_uploaded\media_1789678818712.png" (
    copy /y "%BRAIN_DIR%\.user_uploaded\media_1789678818712.png" "assets\web_ui_dashboard.png" >nul
    echo  [+] Copied assets\web_ui_dashboard.png
)

:: 4. 3D Canvas WebGL Render
if exist "%BRAIN_DIR%\canvas_render_1789682180432.png" (
    copy /y "%BRAIN_DIR%\canvas_render_1789682180432.png" "assets\simulation_environment_3d.png" >nul
    echo  [+] Copied assets\simulation_environment_3d.png
)

echo [INFO] Asset synchronization complete.
