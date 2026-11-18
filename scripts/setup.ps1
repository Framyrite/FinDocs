#requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$TokenDir = Join-Path $Backend "models\multilingual-e5-small"
$Token = Join-Path $TokenDir "tokenizer.json"
$Url = "https://huggingface.co/intfloat/multilingual-e5-small/resolve/ada7b62be30f82b0bc5da131b0477721c8fc14e9/tokenizer.json"
$Sha = "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39"

foreach ($cmd in @("py","node","npm")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Не найдена команда: $cmd" }
}
& node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<12)){console.error("Нужен Node.js 22.12+");process.exit(1)}'
if ($LASTEXITCODE -ne 0) { throw "Несовместимая версия Node.js" }

if (-not (Test-Path $Python)) {
    & py -3.12 -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Не удалось создать Python 3.12 venv" }
}
& $Python -c 'import sys; assert sys.version_info[:2] == (3, 12)'
if ($LASTEXITCODE -ne 0) { throw "Нужен Python 3.12" }

& $Python -m pip install -r (Join-Path $Backend "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { throw "Установка Python-зависимостей не удалась" }
& $Python -m pip check
if ($LASTEXITCODE -ne 0) { throw "Конфликт Python-зависимостей" }

New-Item -ItemType Directory -Force -Path $TokenDir | Out-Null
$Temp = Join-Path $TokenDir ("tokenizer." + [guid]::NewGuid().ToString("N") + ".tmp")
try {
    if (-not (Test-Path $Token)) {
        Invoke-WebRequest -Uri $Url -OutFile $Temp
        $Digest = (Get-FileHash -Path $Temp -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Digest -ne $Sha) { throw "Неправильный SHA-256 токенизатора: $Digest" }
        Move-Item -Path $Temp -Destination $Token
    } else {
        $Digest = (Get-FileHash -Path $Token -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Digest -ne $Sha) { throw "Неправильный SHA-256 токенизатора: $Digest" }
    }
} finally {
    if (Test-Path $Temp) { Remove-Item $Temp -Force }
}

foreach ($Component in @("backend","frontend")) {
    $Env = Join-Path $Root "$Component\.env"
    if (-not (Test-Path $Env)) {
        Copy-Item (Join-Path $Root "$Component\.env.example") $Env
        Write-Host "Создан $Component/.env"
    }
}
Push-Location $Frontend
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci завершился с ошибкой" }
} finally { Pop-Location }
Write-Host "Готово. Ollama и веса моделей устанавливаются отдельно."
