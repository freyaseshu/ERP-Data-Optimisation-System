"""
Unit Test: PostgreSQL Database Connectivity, Schema & Constraints
"""

import unittest
from sqlalchemy import text
from app import create_app
from utils.db import db

class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_01_postgres_connectivity(self):
        """Verify direct PostgreSQL connection and version."""
        with db.engine.connect() as conn:
            ver = conn.execute(text("SELECT version();")).scalar()
            self.assertIsNotNone(ver)
            self.assertIn("PostgreSQL", ver)

    def test_02_all_erp_tables_exist(self):
        """Verify all 10 ERP tables and tracking tables exist in PostgreSQL."""
        expected_tables = [
            'departments', 'employees', 'customers', 'suppliers', 'products',
            'orders', 'order_items', 'inventory', 'payments', 'transactions',
            'users', 'query_performance_logs', 'optimisation_recommendations', 'system_limitations'
        ]
        with db.engine.connect() as conn:
            res = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)).fetchall()
            existing = [r[0] for r in res]

        for tbl in expected_tables:
            self.assertIn(tbl, existing, f"Table '{tbl}' is missing in PostgreSQL schema.")

    def test_03_primary_keys_defined(self):
        """Verify that every core table has a defined PRIMARY KEY."""
        tables = ['customers', 'products', 'orders', 'order_items', 'inventory', 'payments', 'transactions']
        with db.engine.connect() as conn:
            for tbl in tables:
                pk_res = conn.execute(text("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = :tname;
                """), {"tname": tbl}).fetchall()
                self.assertTrue(len(pk_res) > 0, f"Table '{tbl}' lacks a primary key constraint.")

if __name__ == '__main__':
    unittest.main()
