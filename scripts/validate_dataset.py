#!/usr/bin/env python3
"""
ERP Data Optimisation System - Dataset Validation Script
Validates row counts, primary key integrity, and foreign key referential integrity
across all ERP and system tables in PostgreSQL.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/erp_optimisation_db')
if DB_URL.startswith('postgresql+psycopg://'):
    DB_URL = DB_URL.replace('postgresql+psycopg://', 'postgresql://')
elif DB_URL.startswith('postgresql+psycopg2://'):
    DB_URL = DB_URL.replace('postgresql+psycopg2://', 'postgresql://')

ERP_TABLES = [
    'departments', 'employees', 'customers', 'suppliers', 'products',
    'orders', 'order_items', 'inventory', 'payments', 'transactions'
]

SYSTEM_TABLES = [
    'users', 'system_limitations', 'query_performance_logs', 
    'optimisation_recommendations', 'orders_archive', 'archive_logs'
]

INTEGRITY_CHECKS = [
    ("Employees -> Departments FK", "SELECT COUNT(*) FROM employees WHERE department_id IS NOT NULL AND department_id NOT IN (SELECT id FROM departments);"),
    ("Products -> Suppliers FK", "SELECT COUNT(*) FROM products WHERE supplier_id IS NOT NULL AND supplier_id NOT IN (SELECT id FROM suppliers);"),
    ("Orders -> Customers FK", "SELECT COUNT(*) FROM orders WHERE customer_id NOT IN (SELECT id FROM customers);"),
    ("Order Items -> Orders FK", "SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders);"),
    ("Order Items -> Products FK", "SELECT COUNT(*) FROM order_items WHERE product_id NOT IN (SELECT id FROM products);"),
    ("Inventory -> Products FK", "SELECT COUNT(*) FROM inventory WHERE product_id NOT IN (SELECT id FROM products);"),
    ("Payments -> Orders FK", "SELECT COUNT(*) FROM payments WHERE order_id NOT IN (SELECT id FROM orders);"),
    ("Transactions -> Payments FK", "SELECT COUNT(*) FROM transactions WHERE payment_id IS NOT NULL AND payment_id NOT IN (SELECT id FROM payments);")
]

def validate():
    print("=" * 75)
    print("ERP DATASET INTEGRITY & ROW COUNT VALIDATION (PostgreSQL)")
    print("=" * 75)

    try:
        conn = psycopg.connect(DB_URL)
    except Exception as e:
        print(f"[FATAL] Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    print(f"Connected to: {DB_URL.split('@')[-1]}")
    print("-" * 75)
    print(f"{'Table Name':<30} | {'Type':<12} | {'Row Count':>15} | {'Status':<10}")
    print("-" * 75)

    total_erp_records = 0
    total_all_records = 0
    missing_tables = []

    with conn.cursor() as cur:
        for tbl in ERP_TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                cnt = cur.fetchone()[0]
                total_erp_records += cnt
                total_all_records += cnt
                status = "OK" if cnt > 0 else "EMPTY"
                print(f"{tbl:<30} | {'ERP Core':<12} | {cnt:>15,} | {status:<10}")
            except Exception as e:
                print(f"{tbl:<30} | {'ERP Core':<12} | {'ERROR':>15} | MISSING")
                missing_tables.append(tbl)
                conn.rollback()

        for tbl in SYSTEM_TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                cnt = cur.fetchone()[0]
                total_all_records += cnt
                status = "OK" if cnt > 0 else "EMPTY"
                print(f"{tbl:<30} | {'System':<12} | {cnt:>15,} | {status:<10}")
            except Exception as e:
                print(f"{tbl:<30} | {'System':<12} | {'ERROR':>15} | MISSING")
                missing_tables.append(tbl)
                conn.rollback()

    print("-" * 75)
    print(f"{'TOTAL CORE ERP RECORDS':<30} | {'':<12} | {total_erp_records:>15,} | {'':<10}")
    print(f"{'TOTAL DATABASE RECORDS':<30} | {'':<12} | {total_all_records:>15,} | {'':<10}")
    print("=" * 75)

    print("\n--- REFERENTIAL INTEGRITY VERIFICATION ---")
    all_integrity_passed = True
    with conn.cursor() as cur:
        for check_name, query in INTEGRITY_CHECKS:
            try:
                cur.execute(query)
                orphans = cur.fetchone()[0]
                if orphans == 0:
                    print(f"  [PASS] {check_name}: 0 orphan rows")
                else:
                    print(f"  [FAIL] {check_name}: {orphans:,} orphan rows found!")
                    all_integrity_passed = False
            except Exception as e:
                print(f"  [ERROR] {check_name}: {e}")
                all_integrity_passed = False
                conn.rollback()

    conn.close()

    print("\n" + "=" * 75)
    if missing_tables:
        print(f"[FAIL] Missing tables: {', '.join(missing_tables)}")
        sys.exit(1)
    elif not all_integrity_passed:
        print("[FAIL] Referential integrity checks failed!")
        sys.exit(1)
    elif total_erp_records == 0:
        print("[WARNING] ERP tables are empty. Run 'python scripts/generate_dataset.py' to generate records.")
        sys.exit(0)
    else:
        print(f"[SUCCESS] All integrity checks passed! Dataset contains {total_erp_records:,} ERP records.")
        sys.exit(0)

if __name__ == '__main__':
    validate()
