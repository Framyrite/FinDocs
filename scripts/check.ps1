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
    $env:FINDOCS_LLM_PROVIDER = "mock"
    $env:PYTHONPATH = ".."
    & $Python -m pytest tests/ ../tests/ -q
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
} finally { Pop-Location }
Push-Location (Join-Path $Root "frontend")
try {
    & npm run lint
    if ($LASTEXITCODE -ne 0) { throw "npm lint failed" }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm build failed" }
    & npm test -- --run
    if ($LASTEXITCODE -ne 0) { throw "npm tests failed" }
} finally { Pop-Location }
Write-Host "Все проверки успешно завершены."
