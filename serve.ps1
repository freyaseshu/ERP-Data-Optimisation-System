$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $erpPython = Join-Path $PSScriptRoot 'venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $erpPython)) { throw 'Run setup.ps1 first.' }
    if (Test-Path -LiteralPath '.local/pgdata/PG_VERSION') {
        & $erpPython scripts/local_postgres.py start
        if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL failed to start.' }
    }
    & $erpPython serve.py
    exit $LASTEXITCODE
} finally { Pop-Location }
