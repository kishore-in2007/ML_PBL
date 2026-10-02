$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $BackendDir "venv\Scripts\python.exe"

if (!(Test-Path $Python)) {
    throw "Backend venv not found at $Python"
}

Set-Location $BackendDir

& $Python -c "import sys, numpy; print('Backend Python:', sys.executable); print('NumPy:', numpy.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Required runtime modules are missing from Backend\venv"
}

& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
