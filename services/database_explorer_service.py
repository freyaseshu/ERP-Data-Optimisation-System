"""
Database Explorer Service - PostgreSQL Catalog Inspector
Provides table schema discovery, index details, PK/FK relationships,
and server-side paginated data browsing.
"""

from sqlalchemy import text
from utils.db import db

class DatabaseExplorerService:
    ALLOWED_TABLES = [
        'departments', 'employees', 'customers', 'suppliers', 'products',
        'orders', 'order_items', 'inventory', 'payments', 'transactions',
        'users', 'system_limitations', 'query_performance_logs', 
        'optimisation_recommendations', 'orders_archive', 'archive_logs'
    ]

    @classmethod
    def get_tables_summary(cls):
        """
        Lists all ERP and system tables with row counts, total size, and index count.
        """
        summary = []
        try:
            with db.engine.connect() as conn:
                for table in cls.ALLOWED_TABLES:
                    # Get exact row count
                    cnt_res = conn.execute(text(f"SELECT COUNT(*) FROM {table};")).scalar()
                    # Get table size
                    size_res = conn.execute(text(f"SELECT pg_size_pretty(pg_total_relation_size('{table}'));")).scalar()
                    # Get index count
                    idx_res = conn.execute(text(f"SELECT COUNT(*) FROM pg_indexes WHERE tablename = '{table}';")).scalar()
                    
                    summary.append({
                        "name": table,
                        "row_count": cnt_res or 0,
                        "size": size_res or "0 bytes",
                        "index_count": idx_res or 0,
                        "category": "ERP Core" if table not in ['users', 'system_limitations', 'query_performance_logs', 'optimisation_recommendations', 'orders_archive', 'archive_logs'] else "System"
                    })
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": True, "tables": summary}

    @classmethod
    def get_table_details(cls, table_name: str):
        """
        Retrieves column schemas, data types, indexes, and foreign keys for a specific table.
        """
        if table_name not in cls.ALLOWED_TABLES:
            return {"success": False, "error": f"Invalid table '{table_name}'."}

        try:
            with db.engine.connect() as conn:
                # 1. Columns & Data Types
                col_res = conn.execute(text("""
                    SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = :tname
                    ORDER BY ordinal_position;
                """), {"tname": table_name}).fetchall()

                columns = [{
                    "name": r[0],
                    "type": r[1] + (f"({r[2]})" if r[2] else ""),
                    "nullable": r[3] == "YES",
                    "default": r[4]
                } for r in col_res]

                # 2. Indexes
                idx_res = conn.execute(text("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = :tname;
                """), {"tname": table_name}).fetchall()

                indexes = [{
                    "name": r[0],
                    "definition": r[1]
                } for r in idx_res]

                # 3. Foreign Keys
                fk_res = conn.execute(text("""
                    SELECT
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = :tname;
                """), {"tname": table_name}).fetchall()

                foreign_keys = [{
                    "column": r[0],
                    "foreign_table": r[1],
                    "foreign_column": r[2]
                } for r in fk_res]

                # 4. Primary Key
                pk_res = conn.execute(text("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                      ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = :tname;
                """), {"tname": table_name}).fetchall()
                primary_keys = [r[0] for r in pk_res]

            return {
                "success": True,
                "table_name": table_name,
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": foreign_keys,
                "primary_keys": primary_keys
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def get_paginated_records(cls, table_name: str, page: int = 1, per_page: int = 25, search: str = None, sort_by: str = None, sort_dir: str = 'ASC'):
        """
        Fetches paginated records from a table with safe parameterization and sorting.
        """
        if table_name not in cls.ALLOWED_TABLES:
            return {"success": False, "error": f"Invalid table '{table_name}'."}

        page = max(1, page)
        per_page = min(max(5, per_page), 100)
        offset = (page - 1) * per_page
        sort_dir = 'DESC' if str(sort_dir).upper() == 'DESC' else 'ASC'

        try:
            with db.engine.connect() as conn:
                # Get valid columns for this table
                cols_res = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns WHERE table_name = :tname ORDER BY ordinal_position;
                """), {"tname": table_name}).fetchall()
                valid_columns = [r[0] for r in cols_res]

                if not valid_columns:
                    return {"success": False, "error": f"No columns found for {table_name}"}

                # Validate sort_by
                if not sort_by or sort_by not in valid_columns:
                    sort_by = valid_columns[0]

                where_clause = ""
                params = {"limit": per_page, "offset": offset}

                # Simple search across text/varchar columns
                if search and search.strip():
                    search_term = f"%{search.strip()}%"
                    text_cols = conn.execute(text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = :tname AND data_type IN ('character varying', 'text', 'character');
                    """), {"tname": table_name}).fetchall()
                    
                    if text_cols:
                        search_conds = [f"{c[0]} ILIKE :search" for c in text_cols]
                        where_clause = f"WHERE {' OR '.join(search_conds)}"
                        params["search"] = search_term

                # Count total matching rows
                count_sql = f"SELECT COUNT(*) FROM {table_name} {where_clause};"
                total_records = conn.execute(text(count_sql), params).scalar()

                # Fetch rows
                data_sql = f"SELECT * FROM {table_name} {where_clause} ORDER BY {sort_by} {sort_dir} LIMIT :limit OFFSET :offset;"
                result = conn.execute(text(data_sql), params)
                columns = list(result.keys())
                raw_rows = result.fetchall()

                rows = []
                for row in raw_rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        if hasattr(val, 'isoformat'):
                            row_dict[col] = val.isoformat()
                        elif hasattr(val, '__float__'):
                            row_dict[col] = float(val)
                        else:
                            row_dict[col] = str(val) if val is not None else None
                    rows.append(row_dict)

                total_pages = (total_records + per_page - 1) // per_page if total_records else 1

                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": columns,
                    "rows": rows,
                    "page": page,
                    "per_page": per_page,
                    "total_records": total_records,
                    "total_pages": total_pages,
                    "sort_by": sort_by,
                    "sort_dir": sort_dir
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
