"""
Data Archive service.

Currently supports archiving `orders` older than a given date into
`orders_archive`, logging the operation to `archive_logs`. The pattern
is written to be easy to extend to other tables.
"""
from datetime import datetime
from sqlalchemy import text
from utils.db import db
from models.archive_log import ArchiveLog

ARCHIVABLE_TABLES = {
    "orders": {
        "source_table": "orders",
        "archive_table": "orders_archive",
        "date_column": "order_date",
        "columns": ["id", "customer_id", "order_date", "total_amount", "status"],
    }
}


def preview_archive(table_key: str, before_date: str):
    """Returns the count of records that WOULD be archived, without changing data."""
    if table_key not in ARCHIVABLE_TABLES:
        raise ValueError(f"Unsupported table for archiving: {table_key}")

    cfg = ARCHIVABLE_TABLES[table_key]
    query = text(f"""
        SELECT COUNT(*) AS cnt FROM {cfg['source_table']}
        WHERE {cfg['date_column']} < :before_date
    """)
    result = db.session.execute(query, {"before_date": before_date}).scalar()
    return {
        "table": cfg["source_table"],
        "archive_table": cfg["archive_table"],
        "condition": f"{cfg['date_column']} < {before_date}",
        "records_to_archive": result or 0,
    }


def execute_archive(table_key: str, before_date: str, archived_by: str):
    """
    Moves matching records into the archive table inside a single
    transaction: insert into archive -> delete from source -> log.
    Rolls back entirely if any step fails.
    """
    if table_key not in ARCHIVABLE_TABLES:
        raise ValueError(f"Unsupported table for archiving: {table_key}")

    cfg = ARCHIVABLE_TABLES[table_key]

    try:
        select_query = text(f"""
            SELECT id, customer_id, order_date, total_amount, status
            FROM {cfg['source_table']}
            WHERE {cfg['date_column']} < :before_date
        """)
        rows = db.session.execute(select_query, {"before_date": before_date}).mappings().all()

        if not rows:
            return {"records_archived": 0, "message": "No records matched the archive condition."}

        insert_query = text(f"""
            INSERT INTO {cfg['archive_table']}
                (original_order_id, customer_id, order_date, total_amount, status, archived_at)
            VALUES
                (:id, :customer_id, :order_date, :total_amount, :status, :archived_at)
        """)
        now = datetime.utcnow()
        for row in rows:
            db.session.execute(insert_query, {
                "id": row["id"],
                "customer_id": row["customer_id"],
                "order_date": row["order_date"],
                "total_amount": row["total_amount"],
                "status": row["status"],
                "archived_at": now,
            })

        ids = [row["id"] for row in rows]
        placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
        params = {f"id{i}": val for i, val in enumerate(ids)}
        delete_query = text(f"DELETE FROM {cfg['source_table']} WHERE id IN ({placeholders})")
        db.session.execute(delete_query, params)

        log_entry = ArchiveLog(
            table_name=cfg["source_table"],
            records_archived=len(rows),
            archive_date=now,
            archived_by=archived_by,
        )
        db.session.add(log_entry)

        db.session.commit()
        return {"records_archived": len(rows), "message": "Archive completed successfully."}

    except Exception:
        db.session.rollback()
        raise
