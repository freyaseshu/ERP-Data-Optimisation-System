param([switch]$ApproveIndexes, [ValidateRange(1,10)][int]$Iterations = 3)
$ErrorActionPreference = 'Stop'
if (-not $ApproveIndexes) { throw 'Review BENCHMARK_WORKLOAD in services/benchmark_service.py, then pass -ApproveIndexes to allow those indexes.' }
Push-Location $PSScriptRoot
try {
    & ./venv/Scripts/python.exe scripts/run_benchmarks.py --approve-indexes --iterations $Iterations
    exit $LASTEXITCODE
} finally { Pop-Location }
