from sqlalchemy import text, inspect
from utils.db import db
TABLE_CONFIG = {
    'customers': {'table': 'customers', 'group_by': ['email'], 'label': 'Repeated customer emails'},
    'products': {'table': 'products', 'group_by': ['name', 'category', 'unit_price'], 'label': 'Matching product descriptions and prices'},
    'inventory': {'table': 'inventory', 'group_by': ['product_id', 'warehouse_location'], 'label': 'Repeated stock positions'},
    'orders': {'table': 'orders', 'group_by': ['customer_id', 'order_date', 'total_amount'], 'label': 'Potentially repeated orders'},
}

def find_duplicates(table_key):
    if table_key not in TABLE_CONFIG:
        raise ValueError('Unsupported table.')
    cfg = TABLE_CONFIG[table_key]
    columns = ', '.join(cfg['group_by'])
    rows = db.session.execute(text(f'SELECT {columns}, COUNT(*) AS dup_count, array_agg(id ORDER BY id) AS ids FROM {table_key} GROUP BY {columns} HAVING COUNT(*) > 1 ORDER BY dup_count DESC LIMIT 200')).mappings()
    groups = [dict(group_values={c: r[c] for c in cfg['group_by']}, duplicate_count=r['dup_count'], record_ids=r['ids'], suggested_action='Review. Only unreferenced, matching records can be deleted.') for r in rows]
    return {'table': table_key, 'label': cfg['label'], 'group_by': cfg['group_by'], 'duplicate_groups': groups, 'total_groups': len(groups), 'total_duplicate_records': sum(g['duplicate_count'] - 1 for g in groups), 'group_limit': 200}

def delete_duplicates(table_key, keep_id, delete_ids):
    if table_key not in TABLE_CONFIG or not delete_ids or keep_id in delete_ids or len(delete_ids) > 200:
        raise ValueError('Invalid duplicate selection.')
    columns = TABLE_CONFIG[table_key]['group_by']
    try:
        conn = db.session.connection()
        # Block concurrent inserts/references while verifying a small, explicit deletion.
        conn.exec_driver_sql('LOCK TABLE ' + table_key + ' IN EXCLUSIVE MODE')
        records = conn.execute(text('SELECT * FROM ' + table_key + ' WHERE id = ANY(:ids) FOR UPDATE'), {'ids': [keep_id] + delete_ids}).mappings().all()
        if len(records) != len(set([keep_id] + delete_ids)) or len({tuple(r[c] for c in columns) for r in records}) != 1:
            raise ValueError('All selected records must exist and belong to the same duplicate group.')
        for child in inspect(conn).get_table_names(schema='public'):
            for fk in inspect(conn).get_foreign_keys(child, schema='public'):
                if fk['referred_table'] == table_key:
                    for column in fk['constrained_columns']:
                        q = conn.dialect.identifier_preparer.quote
                        if conn.execute(text('SELECT 1 FROM public.' + q(child) + ' WHERE ' + q(column) + ' = ANY(:ids) LIMIT 1'), {'ids': delete_ids}).first():
                            raise ValueError('Referenced records cannot be deleted; related ERP data is preserved.')
        result = conn.execute(text('DELETE FROM ' + table_key + ' WHERE id=ANY(:ids)'), {'ids': delete_ids})
        db.session.commit()
        return result.rowcount
    except Exception:
        db.session.rollback()
        raise
