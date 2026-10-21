$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $erpPython = Join-Path $PSScriptRoot 'venv/Scripts/python.exe'
    if (-not (Test-Path $erpPython)) { throw 'Run setup.ps1 first.' }
    & $erpPython -m pytest -q --junitxml=artifacts/test-results.xml
    exit $LASTEXITCODE
} finally { Pop-Location }
