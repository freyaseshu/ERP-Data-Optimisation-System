"""
Unit Test: SQL Security Guardrails, Destructive Query Rejection & Timeouts
"""

import unittest
from services.query_analyser import QueryAnalyserService

class TestSecurity(unittest.TestCase):
    def test_01_allow_valid_select(self):
        """Verify standard SELECT queries pass security inspection."""
        query = "SELECT id, name FROM customers WHERE city = 'Chicago';"
        is_safe, msg = QueryAnalyserService.is_safe_query(query)
        self.assertTrue(is_safe, f"Expected safe, got: {msg}")

    def test_02_reject_drop_table(self):
        """Verify DROP TABLE queries are blocked."""
        query = "DROP TABLE customers;"
        is_safe, msg = QueryAnalyserService.is_safe_query(query)
        self.assertFalse(is_safe)
        self.assertTrue(any(w in msg.lower() for w in ['rejected', 'only read-only', 'not allowed']))

    def test_03_reject_truncate(self):
        """Verify TRUNCATE queries are blocked."""
        query = "TRUNCATE TABLE orders;"
        is_safe, msg = QueryAnalyserService.is_safe_query(query)
        self.assertFalse(is_safe)
        self.assertTrue(any(w in msg.lower() for w in ['rejected', 'only read-only', 'not allowed']))

    def test_04_reject_delete_and_update(self):
        """Verify DELETE and UPDATE queries are blocked."""
        q_del = "DELETE FROM products WHERE id = 1;"
        q_upd = "UPDATE products SET unit_price = 0;"
        self.assertFalse(QueryAnalyserService.is_safe_query(q_del)[0])
        self.assertFalse(QueryAnalyserService.is_safe_query(q_upd)[0])

    def test_05_reject_semicolon_injection(self):
        """Verify stacked/multiple SQL statements with semicolon injection are rejected."""
        query = "SELECT * FROM customers; DROP TABLE orders;"
        is_safe, msg = QueryAnalyserService.is_safe_query(query)
        self.assertFalse(is_safe)
        self.assertIn("multiple", msg.lower())

if __name__ == '__main__':
    unittest.main()
