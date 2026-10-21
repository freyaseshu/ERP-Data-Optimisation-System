#!/usr/bin/env python3
"""
Master Test Runner - ERP Data Optimisation System
Discovers and executes all unit tests across database, dataset, APIs, optimizer, and security.
"""

import os
import sys
import unittest
import time

# Ensure project root is in path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.test_database import TestDatabase
from tests.test_dataset import TestDataset
from tests.test_api import TestAPI
from tests.test_optimizer import TestOptimizer
from tests.test_security import TestSecurity

def run_tests():
    print("=" * 75)
    print("ERP DATA OPTIMISATION SYSTEM - AUTOMATED TEST SUITE")
    print("PostgreSQL Database & Query Tuning Engine Verification")
    print("=" * 75)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestDataset))
    suite.addTests(loader.loadTestsFromTestCase(TestAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))

    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    print("\n" + "=" * 75)
    print(f"AUTOMATED TEST RESULTS SUMMARY ({duration:.2f} seconds)")
    print("-" * 75)
    print(f"  Tests Executed:  {total:>4}")
    print(f"  Tests Passed:    {passed:>4}")
    print(f"  Tests Failed:    {failures:>4}")
    print(f"  Execution Errors:{errors:>4}")
    print("-" * 75)

    if failures == 0 and errors == 0:
        print("[SUCCESS] All automated test suites passed successfully!")
        sys.exit(0)
    else:
        print("[FAILURE] Some tests failed. Please review the tracebacks above.")
        sys.exit(1)

if __name__ == '__main__':
    run_tests()
