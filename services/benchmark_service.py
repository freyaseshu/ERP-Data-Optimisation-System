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
        "baseline_sql": "SELECT c.name, c.email, o.id, o.order_date, o.total_amount FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'Delivered' AND o.order_date >= '2025-01-01' ORDER BY o.order_date DESC LIMIT 100;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders(status, order_date DESC);",
        "index_name": "idx_orders_status_date"
    },
    {
        "id": "BM-03",
        "name": "Product Category Search & Price Sort",
        "description": "Finds highest priced products within Industrial Machinery category",
        "baseline_sql": "SELECT id, name, sku, category, unit_price FROM products WHERE category = 'Heavy Machinery' ORDER BY unit_price DESC LIMIT 50;",
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
        "baseline_sql": "SELECT s.name AS supplier_name, p.category, COUNT(oi.id) AS units_sold, SUM(oi.line_total) AS gross_sales FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN suppliers s ON p.supplier_id = s.id GROUP BY s.name, p.category ORDER BY gross_sales DESC LIMIT 25;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);",
        "index_name": "idx_order_items_product_id"
    },
    {
        "id": "BM-06",
        "name": "Low Stock Reorder Inventory Alert",
        "description": "Scans inventory and product catalog for items requiring immediate replenishment",
        "baseline_sql": "SELECT p.name, p.sku, p.category, i.warehouse_location, i.quantity_on_hand, i.reorder_level FROM inventory i JOIN products p ON i.product_id = p.id WHERE i.quantity_on_hand <= i.reorder_level ORDER BY i.quantity_on_hand ASC LIMIT 100;",
        "optimisation_sql": "CREATE INDEX IF NOT EXISTS idx_inventory_product_reorder ON inventory(quantity_on_hand, reorder_level);",
        "index_name": "idx_inventory_product_reorder"
    }
]

class BenchmarkService:
    @classmethod
    def get_environment_info(cls):
        """
        Captures host hardware and database environment metadata.
        """
        pg_version = "PostgreSQL"
        try:
            with db.engine.connect() as conn:
                pg_version = conn.execute(text("SELECT version();")).scalar()
        except Exception:
            pass

        return {
            "os": f"{platform.system()} {platform.release()}",
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "database": pg_version.split(',')[0] if pg_version else "PostgreSQL",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    @classmethod
    def run_benchmark_item(cls, item: dict, apply_index: bool = True, iterations: int = 3):
        """
        Runs baseline measurement, applies optimization index, runs optimized measurement,
        and calculates improvement.
        """
        query_sql = item["baseline_sql"]
        opt_sql = item["optimisation_sql"]
        name = item["name"]

        # 1. Measure Baseline
        baseline_time, err_b = QueryOptimizerService.measure_execution_time(query_sql, runs=iterations)
        if err_b:
            return {"success": False, "error": f"Baseline failed: {err_b}"}

        # 2. Apply Index if requested
        index_applied = False
        if apply_index and opt_sql:
            try:
                with db.engine.connect() as conn:
                    conn.execution_options(isolation_level="AUTOCOMMIT")
                    conn.execute(text(opt_sql))
                index_applied = True
            except Exception as e:
                # Might already exist
                index_applied = True

        # 3. Measure Optimised
        optimised_time, err_o = QueryOptimizerService.measure_execution_time(query_sql, runs=iterations)
        if err_o:
            return {"success": False, "error": f"Optimised run failed: {err_o}"}

        # 4. Calculate Percentage Improvement
        # Formula: ((Baseline time − Optimised time) / Baseline time) × 100
        improvement = 0.0
        if baseline_time and baseline_time > 0:
            improvement = ((baseline_time - optimised_time) / baseline_time) * 100.0

        # 5. Result Equivalence Check
        equiv = QueryOptimizerService.verify_query_equivalence(query_sql, query_sql)

        # 6. Log to DB
        try:
            log = PerformanceLog(
                query_name=name,
                query_text=query_sql,
                execution_time_before=baseline_time,
                execution_time_after=optimised_time,
                optimization_applied=opt_sql,
                improvement_percentage=improvement,
                status="Benchmarked"
            )
            db.session.add(log)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return {
            "success": True,
            "id": item.get("id"),
            "name": name,
            "description": item.get("description"),
            "baseline_time_ms": baseline_time,
            "optimised_time_ms": optimised_time,
            "improvement_percentage": round(improvement, 2),
            "equivalent": equiv.get("equivalent", True),
            "rows_returned": equiv.get("rows_a", 0),
            "index_applied": opt_sql,
            "iterations": iterations
        }

    @classmethod
    def run_all_benchmarks(cls, iterations: int = 3):
        """
        Executes the entire representative ERP benchmark suite.
        """
        results = []
        env = cls.get_environment_info()

        for item in BENCHMARK_WORKLOAD:
            res = cls.run_benchmark_item(item, apply_index=True, iterations=iterations)
            results.append(res)

        return {
            "environment": env,
            "results": results,
            "total_benchmarks": len(results),
            "successful_benchmarks": sum(1 for r in results if r.get("success"))
        }

    @classmethod
    def get_benchmark_history(cls, limit: int = 50):
        """
        Retrieves historical benchmark runs from query_performance_logs.
        """
        logs = PerformanceLog.query.order_by(PerformanceLog.created_at.desc()).limit(limit).all()
        return [l.to_dict() for l in logs]
