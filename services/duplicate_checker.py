"""
Duplicate Data Checker service.

Detects likely-duplicate records across customers, products, inventory,
and orders using GROUP BY / HAVING queries, and provides a safe delete
that keeps the earliest record and removes the rest of a duplicate group.
"""
from sqlalchemy import text
from utils.db import db

TABLE_CONFIG = {
    "customers": {
        "table": "customers",
        "group_by": ["email"],
        "label": "Duplicate customer emails",
    },
    "products": {
        "table": "products",
        "group_by": ["name", "category", "price"],
        "label": "Duplicate products (same name, category & price)",
    },
    "inventory": {
        "table": "inventory",
        "group_by": ["product_id", "warehouse_location"],
        "label": "Duplicate inventory records (same product & warehouse)",
    },
    "orders": {
        "table": "orders",
        "group_by": ["customer_id", "order_date", "total_amount"],
        "label": "Duplicate orders (same customer, date & amount)",
    },
}


def find_duplicates(table_key: str):
    if table_key not in TABLE_CONFIG:
        raise ValueError(f"Unsupported table: {table_key}")

    cfg = TABLE_CONFIG[table_key]
    table = cfg["table"]
    group_cols = cfg["group_by"]
    group_cols_sql = ", ".join(group_cols)

    query = text(f"""
        SELECT {group_cols_sql}, COUNT(*) AS dup_count,
               GROUP_CONCAT(id ORDER BY id) AS ids
        FROM {table}
        GROUP BY {group_cols_sql}
        HAVING COUNT(*) > 1
        ORDER BY dup_count DESC
        LIMIT 200
    """)

    rows = db.session.execute(query).mappings().all()

    results = []
    for row in rows:
        row_dict = dict(row)
        ids_raw = row_dict.pop("ids")
        count = row_dict.pop("dup_count")
        ids = [int(x) for x in ids_raw.split(",")] if ids_raw else []
        results.append({
            "group_values": row_dict,
            "duplicate_count": count,
            "record_ids": ids,
            "suggested_action": "Review and keep the earliest record; delete the rest.",
        })

    return {
        "table": table,
        "label": cfg["label"],
        "group_by": group_cols,
        "duplicate_groups": results,
        "total_groups": len(results),
        "total_duplicate_records": sum(r["duplicate_count"] - 1 for r in results),
    }


def delete_duplicates(table_key: str, keep_id: int, delete_ids: list):
    """
    Deletes the given delete_ids from the table, keeping keep_id.
    Uses a transaction so the operation is all-or-nothing.
    """
    if table_key not in TABLE_CONFIG:
        raise ValueError(f"Unsupported table: {table_key}")

    table = TABLE_CONFIG[table_key]["table"]

    delete_ids = [i for i in delete_ids if i != keep_id]
    if not delete_ids:
        return 0

    placeholders = ", ".join(f":id{i}" for i in range(len(delete_ids)))
    params = {f"id{i}": val for i, val in enumerate(delete_ids)}

    query = text(f"DELETE FROM {table} WHERE id IN ({placeholders})")

    try:
        result = db.session.execute(query, params)
        db.session.commit()
        return result.rowcount
    except Exception:
        db.session.rollback()
        raise
