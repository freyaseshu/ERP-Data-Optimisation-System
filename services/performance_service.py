"""
Performance Reports service.

Aggregates data from query_performance_logs, archive_logs, and duplicate
findings to power the dashboard and the Performance Reports page.
"""
import csv
import io
from datetime import datetime, timedelta
from sqlalchemy import func, desc, asc
from utils.db import db
from models.performance_log import QueryPerformanceLog
from models.archive_log import ArchiveLog


def get_dashboard_stats():
    from models.customer import Customer
    from models.product import Product
    from models.order import Order
    from models.inventory import Inventory

    total_customers = db.session.query(func.count(Customer.id)).scalar() or 0
    total_products = db.session.query(func.count(Product.id)).scalar() or 0
    total_orders = db.session.query(func.count(Order.id)).scalar() or 0
    total_inventory = db.session.query(func.count(Inventory.id)).scalar() or 0

    avg_exec_time = db.session.query(
        func.avg(QueryPerformanceLog.execution_time_after)
    ).scalar()

    slow_queries = db.session.query(func.count(QueryPerformanceLog.id)).filter(
        QueryPerformanceLog.execution_time_before > 100
    ).scalar() or 0

    archived_total = db.session.query(
        func.coalesce(func.sum(ArchiveLog.records_archived), 0)
    ).scalar() or 0

    return {
        "total_customers": total_customers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_inventory_items": total_inventory,
        "avg_query_execution_time_ms": round(float(avg_exec_time), 3) if avg_exec_time else 0,
        "slow_queries_detected": slow_queries,
        "archived_records": archived_total,
    }


def _date_filter(range_key, start=None, end=None):
    now = datetime.utcnow()
    if range_key == "today":
        return QueryPerformanceLog.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0)
    if range_key == "7days":
        return QueryPerformanceLog.created_at >= now - timedelta(days=7)
    if range_key == "30days":
        return QueryPerformanceLog.created_at >= now - timedelta(days=30)
    if range_key == "custom" and start and end:
        return QueryPerformanceLog.created_at.between(start, end)
    return None  # no filter -> all time


def get_performance_report(range_key="30days", start=None, end=None):
    query = QueryPerformanceLog.query
    date_condition = _date_filter(range_key, start, end)
    if date_condition is not None:
        query = query.filter(date_condition)

    logs = query.order_by(desc(QueryPerformanceLog.created_at)).all()

    slowest = sorted(
        [l for l in logs if l.execution_time_before is not None],
        key=lambda l: l.execution_time_before, reverse=True
    )[:10]
    fastest = sorted(
        [l for l in logs if l.execution_time_after is not None],
        key=lambda l: l.execution_time_after
    )[:10]

    avg_time = (
        sum(l.execution_time_after or 0 for l in logs) / len(logs)
        if logs else 0
    )
    avg_improvement = (
        sum(l.improvement_percentage or 0 for l in logs) / len(logs)
        if logs else 0
    )

    from services.duplicate_checker import find_duplicates, TABLE_CONFIG
    duplicate_total = 0
    for table_key in TABLE_CONFIG:
        try:
            result = find_duplicates(table_key)
            duplicate_total += result["total_duplicate_records"]
        except Exception:
            pass

    archived_records = db.session.query(
        func.coalesce(func.sum(ArchiveLog.records_archived), 0)
    ).scalar() or 0

    return {
        "slowest_queries": [l.to_dict() for l in slowest],
        "fastest_queries": [l.to_dict() for l in fastest],
        "average_execution_time_ms": round(avg_time, 3),
        "queries_optimized": len(logs),
        "average_improvement_percentage": round(avg_improvement, 2),
        "indexes_suggested": len(logs),
        "duplicate_records_found": duplicate_total,
        "records_archived": archived_records,
        "all_logs": [l.to_dict() for l in logs],
    }


def export_report_csv(range_key="30days", start=None, end=None):
    report = get_performance_report(range_key, start, end)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Query", "Execution Time Before (ms)", "Execution Time After (ms)",
        "Optimization Applied", "Improvement %", "Created At"
    ])
    for row in report["all_logs"]:
        writer.writerow([
            row["id"], row["query_text"], row["execution_time_before"],
            row["execution_time_after"], row["optimization_applied"],
            row["improvement_percentage"], row["created_at"]
        ])
    output.seek(0)
    return output.getvalue()
