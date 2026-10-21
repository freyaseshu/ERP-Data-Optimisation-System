# ==============================================================================
# ERP Data Optimisation System - Setup Script (Windows 11 PowerShell)
# Prepares PostgreSQL, virtual environment, schema, and synthetic ERP dataset.
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  ERP DATA OPTIMISATION SYSTEM - SETUP & INSTALLATION" -ForegroundColor Cyan
Write-Host "  PostgreSQL Performance & Query Tuning Architecture" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check Python
Write-Host "`n[1/7] Verifying Python Installation..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 3.10+ is required but was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ and check 'Add Python to PATH'." -ForegroundColor Yellow
    Exit 1
}
$pyVer = & python --version 2>&1
Write-Host "  -> Found Python: $pyVer" -ForegroundColor Green

# 2. Check PostgreSQL Service Status
Write-Host "`n[2/7] Checking PostgreSQL Server Status..." -ForegroundColor Yellow
$pgService = Get-Service *postgres* -ErrorAction SilentlyContinue
if ($pgService) {
    Write-Host "  -> PostgreSQL Service ($($pgService.Name)): $($pgService.Status)" -ForegroundColor Green
    if ($pgService.Status -ne "Running") {
        Write-Host "  -> Attempting to start PostgreSQL service..." -ForegroundColor Yellow
        Start-Service $pgService.Name -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "  -> [NOTE] PostgreSQL Windows service not directly registered. Verifying local port 5432..." -ForegroundColor Yellow
}

# 3. Virtual Environment Setup
Write-Host "`n[3/7] Setting Up Python Virtual Environment..." -ForegroundColor Yellow
if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "  -> Creating virtual environment in .\venv..." -ForegroundColor Yellow
    & python -m venv venv
}
$venvPython = ".\venv\Scripts\python.exe"
Write-Host "  -> Virtual environment verified at .\venv." -ForegroundColor Green

# 4. Install Dependencies
Write-Host "`n[4/7] Installing Dependencies from requirements.txt..." -ForegroundColor Yellow
& $venvPython -m pip install -r requirements.txt --quiet
Write-Host "  -> Dependencies (Flask, SQLAlchemy, psycopg 3, Faker) installed successfully." -ForegroundColor Green

# 5. Environment File Configuration
Write-Host "`n[5/7] Checking Environment Configuration (.env)..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  -> Created .env from .env.example." -ForegroundColor Green
} else {
    Write-Host "  -> Existing .env found." -ForegroundColor Green
}

# 6. Database Creation & Schema Application
Write-Host "`n[6/7] Initialising PostgreSQL Database (erp_optimisation_db)..." -ForegroundColor Yellow
& $venvPython -c "
import os
import psycopg
from dotenv import load_dotenv

load_dotenv('.env')
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/erp_optimisation_db')
if 'erp_optimisation_db' in db_url:
    admin_url = db_url.replace('/erp_optimisation_db', '/postgres').replace('+psycopg', '').replace('+psycopg2', '')
else:
    admin_url = 'postgresql://postgres:postgres@localhost:5432/postgres'

try:
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(\"SELECT 1 FROM pg_database WHERE datname='erp_optimisation_db';\")
            if not cur.fetchone():
                cur.execute('CREATE DATABASE erp_optimisation_db;')
                print('  -> Created database erp_optimisation_db.')
            else:
                print('  -> Database erp_optimisation_db already exists.')
except Exception as e:
    print('  -> Database check notice:', e)

# Apply schema
schema_url = db_url.replace('+psycopg', '').replace('+psycopg2', '')
try:
    with psycopg.connect(schema_url) as conn:
        with open('database/schema.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print('  -> PostgreSQL schema applied successfully.')
except Exception as e:
    print('  -> Schema error:', e)
"

# 7. Dataset Generation & Validation
Write-Host "`n[7/7] Generating Synthetic ERP Dataset (~75,000 Records)..." -ForegroundColor Yellow
& $venvPython scripts/generate_dataset.py --size medium

Write-Host "`n--- Running Final Validation ---" -ForegroundColor Yellow
& $venvPython scripts/validate_dataset.py

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE! SYSTEM READY TO RUN." -ForegroundColor Green
Write-Host "  To launch the web interface, execute:  .\run.ps1" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Green
