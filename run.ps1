# ==============================================================================
# ERP Data Optimisation System - Run Script (Windows 11 PowerShell)
# Launches the Flask backend and opens the browser.
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  STARTING ERP DATA OPTIMISATION SYSTEM (PostgreSQL Engine)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found at .\venv." -ForegroundColor Red
    Write-Host "Please run .\setup.ps1 first to prepare the environment." -ForegroundColor Yellow
    Exit 1
}

Write-Host "`nLaunching web browser at http://127.0.0.1:5000..." -ForegroundColor Green
Start-Process "http://127.0.0.1:5000"

Write-Host "`nStarting Flask application server on http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "Press CTRL+C at any time to stop the server.`n" -ForegroundColor Yellow

& $venvPython app.py
