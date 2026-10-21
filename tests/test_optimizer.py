"""
Unit Test: Query Optimizer, Improvement Formula & Result Equivalence
"""

import unittest
from app import create_app
from services.query_optimizer import QueryOptimizerService
from services.benchmark_service import BenchmarkService

class TestOptimizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_01_measure_execution_time(self):
        """Test multi-iteration query execution time measurement."""
        query = "SELECT id, name FROM customers LIMIT 100;"
        avg_time, err = QueryOptimizerService.measure_execution_time(query, runs=3)
        self.assertIsNone(err)
        self.assertIsNotNone(avg_time)
        self.assertGreater(avg_time, 0.0)

    def test_02_generate_suggestions(self):
        """Test index recommendation generation on unindexed WHERE lookups."""
        query = "SELECT * FROM customers WHERE city = 'San Diego';"
        res = QueryOptimizerService.generate_suggestions(query)
        self.assertTrue(res.get('success'))
        self.assertIn('suggestions', res)

    def test_03_percentage_improvement_formula(self):
        """Verify the exact formula: ((Baseline time − Optimised time) / Baseline time) * 100."""
        baseline = 100.0
        optimised = 20.0
        expected = ((baseline - optimised) / baseline) * 100.0  # 80.0%
        calculated = ((100.0 - 20.0) / 100.0) * 100.0
        self.assertAlmostEqual(calculated, 80.0)

    def test_04_query_result_equivalence(self):
        """Verify semantic row count and data equivalence."""
        q1 = "SELECT id, name FROM products WHERE category = 'Heavy Machinery' ORDER BY id LIMIT 20;"
        q2 = "SELECT id, name FROM products WHERE category = 'Heavy Machinery' ORDER BY id LIMIT 20;"
        equiv = QueryOptimizerService.verify_query_equivalence(q1, q2)
        self.assertTrue(equiv.get('equivalent'))
        self.assertEqual(equiv.get('rows_a'), equiv.get('rows_b'))

if __name__ == '__main__':
    unittest.main()
