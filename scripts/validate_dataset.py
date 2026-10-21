"""Validate exact counts, foreign keys and order/payment arithmetic."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from utils.db import db
from utils.query_safety import ERP_TABLES
from sqlalchemy import inspect, text

def validate_dataset():
    with db.engine.connect() as conn:
        counts = {t: conn.exec_driver_sql('SELECT count(*) FROM public.' + t).scalar() for t in ERP_TABLES}
        checks = {}
        catalog = inspect(conn)
        for table in ERP_TABLES:
            checks[table + ' primary key'] = bool(catalog.get_pk_constraint(table)['constrained_columns'])
            for fk in catalog.get_foreign_keys(table):
                for local, foreign in zip(fk['constrained_columns'], fk['referred_columns']):
                    n = conn.exec_driver_sql(f'SELECT count(*) FROM {table} c LEFT JOIN {fk["referred_table"]} p ON c.{local}=p.{foreign} WHERE c.{local} IS NOT NULL AND p.{foreign} IS NULL').scalar()
                    checks[table + '.' + local + ' foreign key'] = n == 0
        checks['order totals match items'] = conn.exec_driver_sql('SELECT count(*) FROM orders o LEFT JOIN (SELECT order_id, sum(line_total) AS total FROM order_items GROUP BY order_id) t ON t.order_id=o.id WHERE o.total_amount IS DISTINCT FROM t.total').scalar() == 0
        checks['line totals match quantities and discounts'] = conn.exec_driver_sql('SELECT count(*) FROM order_items WHERE line_total != round(quantity * unit_price * (1-discount), 2)').scalar() == 0
        checks['payments match order totals'] = conn.exec_driver_sql('SELECT count(*) FROM payments p JOIN orders o ON o.id=p.order_id WHERE p.amount != o.total_amount').scalar() == 0
        checks['every ERP table populated'] = all(counts.values())
    return {'success': all(checks.values()), 'counts': counts, 'total_erp_records': sum(counts.values()), 'checks': checks}

if __name__ == '__main__':
    with create_app().app_context():
        result = validate_dataset()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result['success'] else 1)
