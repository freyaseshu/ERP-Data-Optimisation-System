# ==============================================================================
# ERP Data Optimisation System - Test Script (Windows 11 PowerShell)
# Runs complete automated test suite across database, dataset, APIs, and security.
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  RUNNING ERP AUTOMATED TEST SUITE (PostgreSQL Engine)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found at .\venv." -ForegroundColor Red
    Exit 1
}

& $venvPython tests/run_all_tests.py
