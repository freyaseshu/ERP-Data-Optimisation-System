"""
Unit Test: Flask Backend API Endpoints & Route Responses
"""

import unittest
from app import create_app

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def login(self, username="admin", password="password"):
        return self.client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_01_login_flow(self):
        """Test authentication flow."""
        res = self.login()
        self.assertEqual(res.status_code, 200)

    def test_02_dashboard_stats_api(self):
        """Test /api/dashboard/stats returns PostgreSQL system stats."""
        with self.client:
            self.login()
            res = self.client.get('/api/dashboard/stats')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertTrue(data['stats']['db_connected'])
            self.assertGreater(data['stats']['total_erp_records'], 0)

    def test_03_database_explorer_apis(self):
        """Test explorer table list and paginated data."""
        with self.client:
            self.login()
            # Tables list
            res = self.client.get('/api/explorer/tables')
            self.assertEqual(res.status_code, 200)
            self.assertTrue(res.get_json().get('success'))

            # Paginated data
            res_data = self.client.get('/api/explorer/data/customers?page=1&per_page=10')
            self.assertEqual(res_data.status_code, 200)
            d = res_data.get_json()
            self.assertTrue(d.get('success'))
            self.assertEqual(len(d['rows']), 10)

    def test_04_query_analyser_api(self):
        """Test /api/analyse-query with EXPLAIN ANALYZE."""
        with self.client:
            self.login()
            res = self.client.post('/api/analyse-query', json={
                'query': "SELECT id, name, city FROM customers WHERE city = 'Chicago' LIMIT 10;",
                'run_analyze': True
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('planning_time_ms', data)
            self.assertIn('execution_time_ms', data)

    def test_05_limitations_api(self):
        """Test /api/limitations returns all 12 limitations."""
        with self.client:
            self.login()
            res = self.client.get('/api/limitations')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertEqual(data['counts']['total'], 12)

    def test_06_report_csv_export(self):
        """Test /reports/export/csv exports CSV file."""
        with self.client:
            self.login()
            res = self.client.get('/reports/export/csv')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'text/csv')
            self.assertIn('Log ID', res.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()
