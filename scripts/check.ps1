$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = "$Root\.venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

Set-Location $Root
& $Python -m pytest -p no:cacheprovider tests -q

if (-not (Test-Path "$Root\frontend\node_modules")) {
    Write-Warning "frontend/node_modules is missing. Run scripts/bootstrap.ps1 before frontend checks."
    exit 0
}

Push-Location "$Root\frontend"
try {
    & npm.cmd run lint
    & npm.cmd run build
}
finally {
    Pop-Location
}
