param([ValidateSet('small','medium','large')][string]$Size = 'medium')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Install Python 3.10+ and add it to PATH.' }
    if (-not (Test-Path 'venv/Scripts/python.exe')) {
        & python -m venv venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    $erpPython = Join-Path $PSScriptRoot 'venv/Scripts/python.exe'
    & $erpPython -m pip --version
    if ($LASTEXITCODE -ne 0) {
        & $erpPython -m ensurepip --upgrade
        if ($LASTEXITCODE -ne 0) { throw 'Unable to initialise pip in the virtual environment.' }
    }
    & $erpPython -m pip --disable-pip-version-check install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    if (-not (Test-Path '.env')) {
        Copy-Item '.env.example' '.env'
        throw 'Created .env. Configure DATABASE_URL and SECRET_KEY, then rerun setup. PostgreSQL must be installed/running; see README.'
    }
    if (Test-Path '.local/pgdata/PG_VERSION') {
        & $erpPython scripts/local_postgres.py start
        if ($LASTEXITCODE -ne 0) { throw 'Local PostgreSQL failed to start.' }
    }
    & $erpPython scripts/init_db.py --create-database
    if ($LASTEXITCODE -ne 0) { throw 'Database initialisation failed.' }
    & $erpPython scripts/generate_dataset.py --size $Size
    if ($LASTEXITCODE -ne 0) { throw 'Dataset generation failed.' }
    & $erpPython scripts/validate_dataset.py
    if ($LASTEXITCODE -ne 0) { throw 'Dataset validation failed.' }
    Write-Host 'Setup complete. Create a login with: .\venv\Scripts\python.exe scripts/create_user.py'
    Write-Host 'Start the app with: .\run.ps1'
} finally { Pop-Location }
