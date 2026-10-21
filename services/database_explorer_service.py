from decimal import Decimal
from sqlalchemy import text, inspect
from utils.db import db
from utils.query_safety import ERP_TABLES

class DatabaseExplorerService:
    ALLOWED_TABLES = list(ERP_TABLES)

    @classmethod
    def get_tables_summary(cls):
        with db.engine.connect() as conn:
            present = set(inspect(conn).get_table_names(schema='public'))
            summary = []
            for table in cls.ALLOWED_TABLES:
                if table not in present:
                    continue
                summary.append({'name': table, 'row_count': conn.exec_driver_sql('SELECT COUNT(*) FROM public.' + table).scalar(),
                    'size': conn.execute(text('SELECT pg_size_pretty(pg_total_relation_size(to_regclass(:table)))'), {'table': 'public.' + table}).scalar(),
                    'index_count': conn.execute(text("SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND tablename=:table"), {'table': table}).scalar(), 'category': 'ERP Core'})
        return {'success': True, 'tables': summary}

    @classmethod
    def get_table_details(cls, table_name):
        if table_name not in cls.ALLOWED_TABLES:
            return {'success': False, 'error': 'Invalid ERP table.'}
        with db.engine.connect() as conn:
            catalog = inspect(conn)
            columns = [{'name': c['name'], 'type': str(c['type']), 'nullable': c['nullable'], 'default': c['default']} for c in catalog.get_columns(table_name, schema='public')]
            indexes = [dict(row) for row in conn.execute(text("SELECT i.indexname AS name, i.indexdef AS definition, pg_relation_size(s.indexrelid) AS size_bytes, s.idx_scan AS scans FROM pg_indexes i JOIN pg_stat_user_indexes s ON i.schemaname=s.schemaname AND i.indexname=s.indexrelname WHERE i.schemaname='public' AND i.tablename=:table"), {'table': table_name}).mappings()]
            fks = [{'column': c, 'foreign_table': f['referred_table'], 'foreign_column': r} for f in catalog.get_foreign_keys(table_name, schema='public') for c, r in zip(f['constrained_columns'], f['referred_columns'])]
            return {'success': True, 'table_name': table_name, 'columns': columns, 'indexes': indexes, 'foreign_keys': fks, 'primary_keys': catalog.get_pk_constraint(table_name, schema='public')['constrained_columns']}

    @classmethod
    def get_paginated_records(cls, table_name, page=1, per_page=25, search=None, sort_by=None, sort_dir='ASC'):
        if table_name not in cls.ALLOWED_TABLES:
            return {'success': False, 'error': 'Invalid ERP table.'}
        if type(page) is not int or page < 1 or type(per_page) is not int or not 1 <= per_page <= 100:
            return {'success': False, 'error': 'page must be positive and per_page must be between 1 and 100.'}
        if sort_dir.upper() not in ('ASC', 'DESC'):
            return {'success': False, 'error': 'Invalid sort direction.'}
        if search and len(search) > 200:
            return {'success': False, 'error': 'Search is limited to 200 characters.'}
        with db.engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = '5s'")
            columns = inspect(conn).get_columns(table_name, schema='public')
            valid = [c['name'] for c in columns]
            if sort_by is not None and sort_by not in valid:
                return {'success': False, 'error': 'Invalid sort column.'}
            sort_by = sort_by or 'id'
            quote = conn.dialect.identifier_preparer.quote
            where = ''
            params = {'limit': per_page, 'offset': (page - 1) * per_page}
            if search and search.strip():
                terms = [quote(c['name']) + '::text ILIKE :search' for c in columns]
                where = ' WHERE (' + ' OR '.join(terms) + ')'
                params['search'] = '%' + search.strip() + '%'
            table = 'public.' + quote(table_name)
            total = conn.execute(text('SELECT count(*) FROM ' + table + where), params).scalar()
            order = quote(sort_by) + ' ' + sort_dir.upper() + (', id ASC' if sort_by != 'id' else '')
            rows = [dict(r) for r in conn.execute(text('SELECT * FROM ' + table + where + ' ORDER BY ' + order + ' LIMIT :limit OFFSET :offset'), params).mappings()]
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, Decimal):
                        row[key] = str(value)
                    elif hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()
        return {'success': True, 'table_name': table_name, 'columns': valid, 'rows': rows, 'page': page, 'per_page': per_page, 'total_records': total, 'total_pages': max(1, (total + per_page - 1) // per_page), 'sort_by': sort_by, 'sort_dir': sort_dir}
