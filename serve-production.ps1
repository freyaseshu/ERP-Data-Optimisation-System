$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $erpEnvironment = Join-Path $PSScriptRoot '.env.production'
    if (-not (Test-Path -LiteralPath $erpEnvironment)) { throw 'Configure .env.production; see docs/deployment.md.' }
    $env:ERP_ENV_FILE = $erpEnvironment
    $env:APP_ENV = 'production'
    & (Join-Path $PSScriptRoot 'venv/Scripts/python.exe') serve.py
    exit $LASTEXITCODE
} finally { Pop-Location }
