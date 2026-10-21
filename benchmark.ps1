# ==============================================================================
# ERP Data Optimisation System - Benchmark Script (Windows 11 PowerShell)
# Runs representative ERP query benchmarks, measures gains, and exports CSV.
# ==============================================================================

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found at .\venv." -ForegroundColor Red
    Write-Host "Please run .\setup.ps1 first to prepare the environment." -ForegroundColor Yellow
    Exit 1
}

& $venvPython scripts/run_benchmarks.py
