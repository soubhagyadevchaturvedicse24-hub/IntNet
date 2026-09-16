@echo off
title CrimeNet Launcher
echo ===================================================
echo     Starting CrimeNet / Operation Cyber-Shield
echo ===================================================
echo.

:: Change to the directory of this batch file
cd /d "%~dp0"

:: Start the backend server in a separate window
echo Starting Backend Server (Uvicorn)...
start "CrimeNet Backend" cmd /k "python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000"

:: Wait a few seconds for the server to spin up
echo Waiting for server to initialize...
timeout /t 3 /nobreak > nul

:: Open the default web browser to the application
echo Opening Frontend Portal...
start http://127.0.0.1:8000

echo.
echo Application started successfully!
echo The backend is running in the newly opened console window.
echo You can safely close this launcher window.
timeout /t 5 > nul
