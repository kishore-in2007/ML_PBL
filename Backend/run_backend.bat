@echo off
setlocal
cd /d "%~dp0"
set PYTHON=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON%" (
  echo Backend venv not found at "%PYTHON%"
  exit /b 1
)
"%PYTHON%" -c "import sys, numpy; print('Backend Python:', sys.executable); print('NumPy:', numpy.__version__)"
if errorlevel 1 exit /b 1
"%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
