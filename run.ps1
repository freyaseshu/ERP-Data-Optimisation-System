$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $erpPython = Join-Path $PSScriptRoot 'venv/Scripts/python.exe'
    if (-not (Test-Path $erpPython)) { throw 'Run setup.ps1 first.' }
    if (Test-Path '.local/pgdata/PG_VERSION') {
        & $erpPython scripts/local_postgres.py start
        if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL failed to start.' }
    }
    Write-Host 'Open http://127.0.0.1:5000. Press Ctrl+C to stop Flask.'
    & $erpPython app.py
    exit $LASTEXITCODE
} finally { Pop-Location }
