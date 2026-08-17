$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "$Root\.venv")) {
    python -m venv "$Root\.venv"
}

$Python = "$Root\.venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r "$Root\backend\requirements.txt"

Push-Location "$Root\frontend"
try {
    & npm.cmd install
}
finally {
    Pop-Location
}

Write-Host "ModelCouncil dependencies installed."
Write-Host "Backend:  $Python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host "Frontend: cd `"$Root\frontend`"; npm.cmd run dev"
