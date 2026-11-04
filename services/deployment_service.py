"""Read-only deployment checks. Never print connection strings or passwords."""
from sqlalchemy import text
from flask import current_app
from utils.db import db
from utils.query_safety import ERP_TABLES


def schema_ready(conn):
    quote = conn.dialect.identifier_preparer.quote
    for table in db.metadata.sorted_tables:
        columns = ', '.join(quote(column.name) for column in table.columns)
        conn.exec_driver_sql(f'SELECT {columns} FROM public.{quote(table.name)} LIMIT 0')


def readiness():
    try:
        with db.engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = '3s'")
            schema_ready(conn)
        if 'readonly' in db.engines:
            with db.engines['readonly'].begin() as conn:
                conn.exec_driver_sql("SET LOCAL statement_timeout = '3s'")
                for table in ERP_TABLES:
                    conn.exec_driver_sql('SELECT id FROM public.' + table + ' LIMIT 0')
        return True
    except Exception:
        return False


def deployment_checks():
    production = current_app.config['APP_ENV'] == 'production'
    checks = [{'name': 'configuration', 'passed': True, 'detail': 'Production settings validated.' if production else 'Local presentation mode; use APP_ENV=production for a hosted server.'}]
    try:
        with db.engine.begin() as conn:
            conn.exec_driver_sql("SET LOCAL statement_timeout = '3s'")
            schema_ready(conn)
            checks.append({'name': 'schema', 'passed': True, 'detail': 'All mapped tables and columns are accessible.'})
            role = conn.exec_driver_sql('SELECT current_user').scalar()
            database = conn.exec_driver_sql('SELECT current_database()').scalar()
            flags = conn.execute(text('SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user')).one()
            safe_role = not any(flags)
            checks.append({'name': 'application_role', 'passed': safe_role or not production,
                           'detail': 'Restricted application role.' if safe_role else 'Privileged database account: replace with a dedicated non-superuser database owner before production.'})
            can_create = conn.exec_driver_sql("SELECT has_database_privilege(current_database(), 'CREATE') AND has_schema_privilege('public', 'CREATE')").scalar()
            checks.append({'name': 'optimization_permissions', 'passed': bool(can_create), 'detail': 'Index ownership and database CREATE are needed for approved optimizations and sandbox schemas.'})
            owns_tables = all(conn.execute(text("SELECT pg_has_role(relowner, 'USAGE') FROM pg_class WHERE oid=to_regclass(:name)"), {'name': 'public.' + table}).scalar() for table in ERP_TABLES)
            checks.append({'name': 'erp_table_ownership', 'passed': owns_tables, 'detail': 'Application role must own ERP tables or inherit the owning role to create approved indexes.'})
            admin = conn.exec_driver_sql("SELECT EXISTS (SELECT 1 FROM public.users WHERE role='Admin')").scalar()
            checks.append({'name': 'administrator', 'passed': bool(admin), 'detail': 'At least one Admin account is required.'})
        if 'readonly' not in db.engines:
            checks.append({'name': 'restricted_reader', 'passed': not production, 'detail': 'No independent reader configured.'})
        else:
            with db.engines['readonly'].begin() as conn:
                conn.exec_driver_sql("SET LOCAL statement_timeout = '3s'")
                reader = conn.exec_driver_sql('SELECT current_user, current_database()').one()
                flags = conn.exec_driver_sql('SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=current_user').one()
                writer_url, reader_url = db.engine.url, db.engines['readonly'].url
                same_target = (writer_url.host, writer_url.port or 5432, writer_url.database) == (reader_url.host, reader_url.port or 5432, reader_url.database)
                allowed = same_target and reader[0] != role and reader[1] == database and not any(flags)
                for table in ERP_TABLES:
                    conn.exec_driver_sql('SELECT id FROM public.' + table + ' LIMIT 0')
                    allowed = allowed and not conn.execute(text("SELECT has_table_privilege(:table, 'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')"), {'table': 'public.' + table}).scalar()
                for table in set(db.metadata.tables) - set(ERP_TABLES):
                    allowed = allowed and not conn.execute(text("SELECT has_table_privilege(:table, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')"), {'table': 'public.' + table}).scalar()
                allowed = allowed and not conn.exec_driver_sql("SELECT has_schema_privilege('public', 'CREATE') OR has_database_privilege(current_database(), 'CREATE')").scalar()
                checks.append({'name': 'restricted_reader', 'passed': bool(allowed), 'detail': 'Reader must be distinct, on the same database, nonprivileged, and limited to ERP SELECT access.'})
    except Exception:
        checks.append({'name': 'database', 'passed': False, 'detail': 'Connection, schema or privileges failed. Run initialization and check private database configuration.'})
    return {'success': all(check['passed'] for check in checks), 'mode': current_app.config['APP_ENV'], 'checks': checks}
