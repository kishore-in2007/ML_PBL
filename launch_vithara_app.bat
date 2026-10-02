@echo off
title Vithara Recovery Monitor Launcher
echo =====================================================================
echo           VITHARA RECOVERY MONITOR - FULL STACK SYSTEM
echo           Multi-Task AI: VitharaNet-Scratch ONNX (94.7% Dice)
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
cd Backend
start "Vithara Backend API" cmd /c "venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Starting React + Vite Frontend on http://localhost:5173 ...
cd ..\Frontend
start "Vithara Frontend Web" cmd /c "npm.cmd run dev"

timeout /t 3 >nul
echo.
echo [+] Opening Vithara Web Application in your browser...
start http://localhost:5173

echo.
echo =====================================================================
echo  Vithara is now running!
echo  Web URL    : http://localhost:5173
echo  Backend API: http://127.0.0.1:8000/docs
echo  Android APK: Vithara-Recovery-App.apk (4.18 MB)
echo =====================================================================
pause
