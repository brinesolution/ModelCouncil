param(
    [switch]$NoBrowser,
    [switch]$SkipChecks
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$NodeModules = Join-Path $FrontendRoot "node_modules"
$FrontendEnv = Join-Path $FrontendRoot ".env.local"
$FrontendEnvExample = Join-Path $FrontendRoot ".env.example"
$RootEnv = Join-Path $ProjectRoot ".env"

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not (Test-Path $Path)) {
        throw $Message
    }
}

Write-Host "ModelCouncil local development launcher" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"

if (-not $SkipChecks) {
    Assert-PathExists $BackendPython "Python virtual environment was not found. Run .\scripts\bootstrap.ps1 first."
    Assert-PathExists $FrontendRoot "Frontend directory was not found at $FrontendRoot."
    Assert-PathExists $NodeModules "Frontend packages are not installed. Run .\scripts\bootstrap.ps1 first."

    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw "npm.cmd was not found on PATH. Install Node.js or fix the Node.js PATH entry."
    }

    if (-not (Test-Path $RootEnv)) {
        Write-Warning "Root .env is missing. The current deterministic simulation can still run, but DeepSeek-backed dialogue will not work until .env is configured."
    }

    $ExpectedFrontendApiBase = "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1"
    $FrontendEnvNeedsRepair = -not (Test-Path $FrontendEnv)

    if (-not $FrontendEnvNeedsRepair) {
        $FrontendEnvContents = Get-Content $FrontendEnv -Raw
        $FrontendEnvNeedsRepair = $FrontendEnvContents -notmatch "NEXT_PUBLIC_API_BASE_URL=http://127\.0\.0\.1:8000/api/v1"
    }

    if ($FrontendEnvNeedsRepair) {
        Write-Host "Creating/repairing frontend/.env.local for the local FastAPI v1 endpoint..." -ForegroundColor Yellow
        Set-Content -Path $FrontendEnv -Value $ExpectedFrontendApiBase -Encoding UTF8
    }

    Write-Host "Running a quick backend health test suite..." -ForegroundColor DarkCyan
    & $BackendPython -m pytest -q tests\backend\test_api.py
    if ($LASTEXITCODE -ne 0) {
        throw "Backend API tests failed. Development servers were not started."
    }
}

$BackendCommand = @"
Set-Location '$ProjectRoot'
Write-Host 'ModelCouncil Backend — FastAPI :8000' -ForegroundColor Cyan
& '$BackendPython' -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
"@

$FrontendCommand = @"
Set-Location '$FrontendRoot'
Write-Host 'ModelCouncil Frontend — Next.js :3000' -ForegroundColor Green
npm.cmd run dev
"@

Write-Host "Starting FastAPI in a new PowerShell window..." -ForegroundColor Cyan
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $BackendCommand
)

Start-Sleep -Seconds 2

Write-Host "Starting Next.js in a new PowerShell window..." -ForegroundColor Green
Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $FrontendCommand
)

if (-not $NoBrowser) {
    Write-Host "Opening http://localhost:3000 ..." -ForegroundColor Magenta
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:3000"
}

Write-Host ""
Write-Host "Development services launched." -ForegroundColor Green
Write-Host "Frontend:     http://localhost:3000"
Write-Host "Simulation:   http://localhost:3000/simulate"
Write-Host "Backend:      http://127.0.0.1:8000"
Write-Host "FastAPI docs: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Close the two spawned PowerShell windows or press Ctrl+C in each to stop the servers."
