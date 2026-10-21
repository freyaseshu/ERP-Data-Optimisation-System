"""Non-destructive order snapshot archive. All live ERP relationships are preserved."""
from datetime import date
from sqlalchemy import text
from utils.db import db
from models.archive_log import ArchiveLog
ARCHIVABLE_TABLES = {'orders': {'source_table': 'orders', 'archive_table': 'orders_archive'}}

def cutoff(table_key, before_date):
    if table_key not in ARCHIVABLE_TABLES:
        raise ValueError('Unsupported archive table.')
    try:
        return date.fromisoformat(before_date)
    except (TypeError, ValueError):
        raise ValueError('A valid ISO date is required.') from None

def preview_archive(table_key, before_date):
    day = cutoff(table_key, before_date)
    count = db.session.execute(text('SELECT count(*) FROM orders o WHERE o.order_date < :day AND NOT EXISTS (SELECT 1 FROM orders_archive a WHERE a.original_order_id=o.id)'), {'day': day}).scalar()
    return {'table': 'orders', 'archive_table': 'orders_archive', 'condition': 'order_date < ' + day.isoformat(), 'records_to_archive': count}

def execute_archive(table_key, before_date, archived_by):
    day = cutoff(table_key, before_date)
    try:
        result = db.session.execute(text('INSERT INTO orders_archive (original_order_id, customer_id, order_date, total_amount, status, archived_at) SELECT id, customer_id, order_date, total_amount, status, CURRENT_TIMESTAMP FROM orders WHERE order_date < :day ON CONFLICT (original_order_id) DO NOTHING'), {'day': day})
        db.session.add(ArchiveLog(table_name='orders', records_archived=result.rowcount, archived_by=archived_by))
        db.session.commit()
        return {'records_archived': result.rowcount, 'message': 'Order snapshots saved; live orders and related data preserved.'}
    except Exception:
        db.session.rollback()
        raise
