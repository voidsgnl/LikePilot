@echo off
title LikePilot Background Service
echo ==========================================
echo   LikePilot - Silent Background Launcher
echo ==========================================
echo.
echo Starting LikePilot automation engine...
echo Dashboard will be available at: http://localhost:5000
echo.
echo [OK] Launching farm.py in detached process...
echo [INFO] You can close this window; the bot will keep running.
echo [INFO] To stop the bot, close Chrome windows or kill 'python.exe' in Task Manager.
echo.

:: Start the process in the background (DETACHED_PROCESS)
start /B python farm.py

:: Wait a moment for startup
timeout /t 3 /nobreak > nul

echo.
echo ==========================================
echo   LikePilot is now running in background!
echo ==========================================
echo.
pause
