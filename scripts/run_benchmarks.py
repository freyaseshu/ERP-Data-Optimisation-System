#!/usr/bin/env python3
"""
ERP Performance Benchmarking Suite CLI Runner
Executes 6 representative ERP workloads, measures baseline vs optimised execution times,
calculates percentage improvements, verifies result equivalence, and exports results to CSV.
"""

import os
import sys
import csv
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from services.benchmark_service import BenchmarkService

def main():
    app = create_app()
    with app.app_context():
        print("=" * 85)
        print("ERP ENTERPRISE BENCHMARKING SUITE - POSTGRESQL ENGINE")
        print("=" * 85)

        print("\nCapturing Environment Details...")
        env = BenchmarkService.get_environment_info()
        print(f"  Host OS:       {env['os']} ({env['architecture']})")
        print(f"  Database:      {env['database']}")
        print(f"  Python:        {env['python_version']}")
        print("-" * 85)

        print("Executing 6 Representative ERP Enterprise Workloads (3 Runs Average each)...")
        t_start = time.time()
        suite_res = BenchmarkService.run_all_benchmarks(iterations=3)
        results = suite_res['results']
        elapsed = time.time() - t_start

        print("\n" + "=" * 90)
        print(f"{'ID':<7} | {'Workload Name':<32} | {'Base (ms)':>10} | {'Opt (ms)':>10} | {'Gain (%)':>10} | {'Equiv':<7}")
        print("=" * 90)

        csv_rows = []
        for r in results:
            equiv_str = 'PASS' if r.get('equivalent') else 'FAIL'
            gain_str = f"{r.get('improvement_percentage', 0):+.1f}%"
            print(f"{r['id']:<7} | {r['name'][:32]:<32} | {r['baseline_time_ms']:>10.2f} | {r['optimised_time_ms']:>10.2f} | {gain_str:>10} | {equiv_str:<7}")

            csv_rows.append({
                'Workload ID': r['id'],
                'Workload Name': r['name'],
                'Baseline Time (ms)': r['baseline_time_ms'],
                'Optimised Time (ms)': r['optimised_time_ms'],
                'Improvement (%)': r['improvement_percentage'],
                'Equivalence': equiv_str,
                'Applied Index': r.get('index_applied', '')
            })

        print("=" * 90)
        print(f"Benchmark completed in {elapsed:.2f} seconds.")

        # Save to tests/benchmark_results.csv and tests/results_before.csv / results_after.csv
        csv_file = os.path.join(PROJECT_ROOT, 'tests', 'benchmark_results.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)

        print(f"[SUCCESS] Exported benchmark results to: {csv_file}\n")

if __name__ == '__main__':
    main()
