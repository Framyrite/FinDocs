#requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Сначала выполните .\scripts\setup.ps1" }
Push-Location (Join-Path $Root "backend")
try {
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "pip check failed" }
    & $Python -m ruff check . ../tests/
    if ($LASTEXITCODE -ne 0) { throw "ruff check failed" }
    & $Python -m ruff format --check . ../tests/
    if ($LASTEXITCODE -ne 0) { throw "ruff format failed" }
    $PreviousProvider = [Environment]::GetEnvironmentVariable("FINDOCS_LLM_PROVIDER", "Process")
    $PreviousPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
    try {
        $env:FINDOCS_LLM_PROVIDER = "mock"
        $env:PYTHONPATH = ".."
        & $Python -m pytest tests/ ../tests/ -q
        if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    } finally {
        [Environment]::SetEnvironmentVariable("FINDOCS_LLM_PROVIDER", $PreviousProvider, "Process")
        [Environment]::SetEnvironmentVariable("PYTHONPATH", $PreviousPythonPath, "Process")
    }
} finally { Pop-Location }
Push-Location (Join-Path $Root "frontend")
try {
    & npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "npm lint failed" }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "npm build failed" }
    & npm.cmd test -- --run
    if ($LASTEXITCODE -ne 0) { throw "npm tests failed" }
} finally { Pop-Location }
Write-Host "Все проверки успешно завершены."
