"""
Benchmark Service - PostgreSQL Performance Benchmarking Suite
Executes representative ERP enterprise workloads, records baseline vs optimised timings,
calculates percentage improvements, verifies result equivalence, and logs results.
"""

import time
import platform
from sqlalchemy import text
from utils.db import db
from models.performance_log import PerformanceLog
from services.query_analyser import QueryAnalyserService
from services.query_optimizer import QueryOptimizerService

BENCHMARK_WORKLOAD = [
    {
        "id": "BM-01",
        "name": "Customer City Filter & Retrieval",
        "description": "Filters customers by geographical market (city = 'Chicago')",
        "baseline_sql": "SELECT id, name, email, city, customer_segment FROM customers WHERE city = 'Chicago';",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_customers_city ON customers(city);",
        "index_name": "idx_customers_city"
    },
    {
        "id": "BM-02",
        "name": "Delivered Orders Customer Join",
        "description": "Joins customers and orders for completed deliveries with order date range",
        "baseline_sql": "SELECT c.name, c.email, o.id, o.order_date, o.total_amount FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'Delivered' AND o.order_date >= '2025-01-01' ORDER BY o.order_date DESC, o.id DESC LIMIT 100;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date DESC);",
        "index_name": "idx_orders_status_date"
    },
    {
        "id": "BM-03",
        "name": "Product Category Search & Price Sort",
        "description": "Finds highest priced products within Industrial Machinery category",
        "baseline_sql": "SELECT id, name, sku, category, unit_price FROM products WHERE category = 'Heavy Machinery' ORDER BY unit_price DESC, id LIMIT 50;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_products_cat_price ON products(category, unit_price DESC);",
        "index_name": "idx_products_cat_price"
    },
    {
        "id": "BM-04",
        "name": "Order Status Revenue Aggregation",
        "description": "Aggregates volume, total gross revenue, and average order value across order statuses",
        "baseline_sql": "SELECT status, COUNT(id) AS total_orders, SUM(total_amount) AS total_revenue, AVG(total_amount) AS avg_order_value FROM orders GROUP BY status;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);",
        "index_name": "idx_orders_status"
    },
    {
        "id": "BM-05",
        "name": "Multi-Tier Supply Chain Sales by Supplier",
        "description": "Joins Order Items, Products, and Suppliers to aggregate top supplier revenues",
        "baseline_sql": "SELECT s.name AS supplier_name, p.category, COUNT(oi.id) AS units_sold, SUM(oi.line_total) AS gross_sales FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN suppliers s ON p.supplier_id = s.id GROUP BY s.name, p.category ORDER BY gross_sales DESC, s.name, p.category LIMIT 25;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);",
        "index_name": "idx_order_items_product_id"
    },
    {
        "id": "BM-06",
        "name": "Low Stock Reorder Inventory Alert",
        "description": "Scans inventory and product catalog for items requiring immediate replenishment",
        "baseline_sql": "SELECT p.name, p.sku, p.category, i.warehouse_location, i.quantity_on_hand, i.reorder_level FROM inventory i JOIN products p ON i.product_id = p.id WHERE i.quantity_on_hand <= i.reorder_level ORDER BY i.quantity_on_hand ASC, i.id ASC LIMIT 100;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_inventory_product_reorder ON inventory(quantity_on_hand, reorder_level);",
        "index_name": "idx_inventory_product_reorder"
    }
    ,{
        "id": "BM-07",
        "name": "Payment Transaction Ledger Lookup",
        "description": "Trace ledger entries through payments and orders to a customer",
        "baseline_sql": "SELECT t.id, t.account_code, t.amount, p.transaction_ref, o.id AS order_id, c.name FROM transactions t JOIN payments p ON p.id=t.payment_id JOIN orders o ON o.id=p.order_id JOIN customers c ON c.id=o.customer_id WHERE t.payment_id=(SELECT min(id) FROM payments) ORDER BY t.id;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_transactions_payment_id ON transactions(payment_id);",
        "index_name": "idx_transactions_payment_id"
    }
]

class BenchmarkService:
    @classmethod
    def get_environment_info(cls):
        from datetime import datetime, timezone
        import os
        result = {'os': f'{platform.system()} {platform.release()}', 'architecture': platform.machine(),
                  'python_version': platform.python_version(), 'cpu_count': os.cpu_count(),
                  'database': 'Unavailable', 'timestamp': datetime.now(timezone.utc).isoformat()}
        try:
            with db.engine.connect() as conn:
                result['database'] = conn.execute(text('SELECT version()')).scalar()
                result['configuration'] = {key: conn.exec_driver_sql('SHOW ' + key).scalar() for key in ('shared_buffers', 'work_mem', 'effective_cache_size', 'max_connections')}
        except Exception:
            result['error'] = 'PostgreSQL unavailable.'
        return result

    @classmethod
    def run_comparison(cls, query, ddl, name, iterations=3):
        import re
        from sqlalchemy import inspect
        from utils.query_safety import validate, ERP_TABLES
        try:
            sql = validate(query)
            ddl = re.sub(r'(?<=[a-z0-9_])\(', ' (', ddl)
            if type(iterations) is not int or not 1 <= iterations <= 10:
                raise ValueError('iterations must be an integer from 1 to 10.')
            # This grammar accepts identifiers/columns only, never expressions or stacked DDL.
            match = re.fullmatch(r'CREATE INDEX IF NOT EXISTS ([a-z_][a-z_0-9]*) ON ([a-z_][a-z_0-9]*) \(([a-z_][a-z_0-9]*(?: DESC| ASC)?(?:, [a-z_][a-z_0-9]*(?: DESC| ASC)?)*)\);?', ddl)
            if not match or match[2] not in ERP_TABLES:
                raise ValueError('Unsupported index definition.')
            index_name, table, columns_sql = match.groups()
            columns = [c.split()[0] for c in columns_sql.split(', ')]
            env = cls.get_environment_info()
            with db.engine.begin() as conn:
                conn.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
                conn.exec_driver_sql("SET LOCAL lock_timeout = '2s'")
                conn.exec_driver_sql('SET LOCAL search_path TO pg_catalog, public')
                if not conn.exec_driver_sql('SELECT pg_try_advisory_xact_lock(620432)').scalar():
                    raise ValueError('Another benchmark is running; retry when it finishes.')
                # Prevent changes during comparison and serialize approved index benchmarks.
                conn.exec_driver_sql('LOCK TABLE ' + ', '.join(ERP_TABLES) + ' IN SHARE MODE')
                catalog = inspect(conn)
                valid_columns = {c['name'] for c in catalog.get_columns(table)}
                if not set(columns) <= valid_columns:
                    raise ValueError('Index columns do not exist.')
                existing = catalog.get_indexes(table)
                existing_name = conn.execute(text('SELECT to_regclass(:name)'), {'name': 'public.' + index_name}).scalar()
                if existing_name and not any(i['name'] == index_name and i['column_names'] == columns and not i.get('dialect_options', {}).get('postgresql_where') for i in existing):
                    raise ValueError('Index name is already used by a different relation.')
                already_present = any(i['column_names'][:len(columns)] == columns for i in existing if i['column_names'] and not i.get('dialect_options', {}).get('postgresql_where'))
                dataset = {t: conn.exec_driver_sql('SELECT count(*) FROM ' + t).scalar() for t in ERP_TABLES}
                before = QueryOptimizerService.sample(conn, sql, iterations)
                if not already_present:
                    conn.exec_driver_sql(ddl)
                after = QueryOptimizerService.sample(conn, sql, iterations)
                equivalent = before['fingerprint'] == after['fingerprint']
                if not equivalent:
                    raise ValueError('Query results changed. Index creation and benchmark were rolled back.')
                improvement = ((before['mean_ms'] - after['mean_ms']) / before['mean_ms'] * 100) if before['mean_ms'] > 0 else None
                size = conn.execute(text('SELECT pg_relation_size(to_regclass(:name))'), {'name': 'public.' + index_name}).scalar() if not already_present else None
                details = {'environment': env, 'dataset_counts': dataset, 'iterations': iterations,
                           'baseline_samples_ms': before['samples_ms'], 'optimised_samples_ms': after['samples_ms'],
                           'baseline_stddev_ms': before['stddev_ms'], 'optimised_stddev_ms': after['stddev_ms'],
                           'baseline_plan': before['plan'], 'optimised_plan': after['plan'], 'equivalent': equivalent,
                           'rows_returned': after['rows'], 'index_created': not already_present, 'index_already_present': already_present,
                           'index_size_bytes': size, 'measurement': 'PostgreSQL EXPLAIN ANALYZE Execution Time; one warm-up each; identical snapshot; row multiset hashes ignore ordering',
                           'note': 'Existing index retained; repeated measurement without a new optimisation.' if already_present else 'New index created. Storage and write overhead are not included in read timings.'}
                # Save the evidence in the SAME transaction as the index; failure rolls both back.
                conn.execute(PerformanceLog.__table__.insert().values(query_name=name, query_text=sql,
                    execution_time_before=before['mean_ms'], execution_time_after=after['mean_ms'],
                    optimization_applied=None if already_present else ddl, improvement_percentage=improvement,
                    status='Benchmarked', details=details))
            return {'success': True, 'name': name, 'baseline_time_ms': before['mean_ms'], 'optimised_time_ms': after['mean_ms'],
                    'time_before': before['mean_ms'], 'time_after': after['mean_ms'], 'improvement': improvement,
                    'improvement_percentage': improvement, 'equivalent': equivalent, 'rows_returned': after['rows'],
                    'index_applied': None if already_present else ddl, 'iterations': iterations, **details}
        except ValueError as exc:
            return {'success': False, 'error': str(exc)}
        except Exception as exc:
            from flask import current_app
            current_app.logger.warning('Benchmark failed (%s)', type(exc).__name__)
            return {'success': False, 'error': 'Benchmark failed; no index was committed. Check PostgreSQL, schema, locks and timeouts.'}

    @classmethod
    def run_benchmark_item(cls, item, apply_index=True, iterations=3):
        if not apply_index:
            return {'success': False, 'error': 'Index approval is required.'}
        return {**cls.run_comparison(item['baseline_sql'], item['optimisation_sql'], item['name'], iterations), 'id': item['id']}

    @classmethod
    def run_all_benchmarks(cls, iterations=3):
        results = [cls.run_benchmark_item(item, iterations=iterations) for item in BENCHMARK_WORKLOAD]
        return {'success': all(r['success'] for r in results), 'environment': cls.get_environment_info(), 'results': results,
                'total_benchmarks': len(results), 'successful_benchmarks': sum(r['success'] for r in results)}

    @classmethod
    def get_benchmark_history(cls, limit=50):
        logs = PerformanceLog.query.filter_by(status='Benchmarked').order_by(PerformanceLog.created_at.desc()).limit(max(1, min(limit, 100))).all()
        return [log.to_dict() for log in logs]
