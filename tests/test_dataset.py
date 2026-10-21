"""
Unit Test: ERP Dataset Size, Volume Requirements & Referential Integrity
"""

import unittest
from sqlalchemy import text
from app import create_app
from utils.db import db

class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_01_total_dataset_volume(self):
        """Verify total records meet the 50,000–100,000 requirement."""
        tables = [
            'departments', 'employees', 'customers', 'suppliers', 'products',
            'orders', 'order_items', 'inventory', 'payments', 'transactions'
        ]
        total_rows = 0
        with db.engine.connect() as conn:
            for tbl in tables:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl};")).scalar()
                total_rows += cnt

        self.assertGreaterEqual(total_rows, 50000, 
            f"Dataset contains {total_rows:,} records, which is less than the required 50,000 records.")

    def test_02_referential_integrity(self):
        """Verify 0 orphan foreign key rows across all related ERP tables."""
        fk_checks = [
            ("Employees -> Departments", "SELECT COUNT(*) FROM employees WHERE department_id IS NOT NULL AND department_id NOT IN (SELECT id FROM departments);"),
            ("Products -> Suppliers", "SELECT COUNT(*) FROM products WHERE supplier_id IS NOT NULL AND supplier_id NOT IN (SELECT id FROM suppliers);"),
            ("Orders -> Customers", "SELECT COUNT(*) FROM orders WHERE customer_id NOT IN (SELECT id FROM customers);"),
            ("Order Items -> Orders", "SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT id FROM orders);"),
            ("Order Items -> Products", "SELECT COUNT(*) FROM order_items WHERE product_id NOT IN (SELECT id FROM products);"),
            ("Inventory -> Products", "SELECT COUNT(*) FROM inventory WHERE product_id NOT IN (SELECT id FROM products);"),
            ("Payments -> Orders", "SELECT COUNT(*) FROM payments WHERE order_id NOT IN (SELECT id FROM orders);"),
            ("Transactions -> Payments", "SELECT COUNT(*) FROM transactions WHERE payment_id IS NOT NULL AND payment_id NOT IN (SELECT id FROM payments);")
        ]

        with db.engine.connect() as conn:
            for name, sql in fk_checks:
                orphans = conn.execute(text(sql)).scalar()
                self.assertEqual(orphans, 0, f"Referential integrity failure in {name}: found {orphans} orphan records.")

if __name__ == '__main__':
    unittest.main()
