"""PostgreSQL AST validation plus database-enforced read-only transactions.
Only ERP tables and explicitly approved pure functions are exposed.
"""
from contextlib import contextmanager
from flask import current_app
from pglast import parse_sql
from sqlalchemy import text
from utils.db import db

ERP_TABLES = ('departments', 'employees', 'customers', 'suppliers', 'products', 'orders', 'order_items', 'inventory', 'payments', 'transactions')
PURE_FUNCTIONS = {'count', 'sum', 'avg', 'min', 'max', 'round', 'abs', 'lower', 'upper', 'length', 'coalesce', 'nullif', 'date_trunc', 'extract', 'date_part', 'concat', 'substring', 'trim', 'greatest', 'least', 'row_number', 'rank', 'dense_rank'}

def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from walk(item)

def validate(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 20000:
        raise ValueError('A SQL query of 1 to 20000 characters is required.')
    try:
        statements = parse_sql(query)
    except Exception:
        raise ValueError('Invalid PostgreSQL syntax.') from None
    if len(statements) != 1:
        raise ValueError('Multiple SQL statements are not allowed.')
    tree = statements[0].stmt()
    if '@' not in tree or tree['@'] != 'SelectStmt':
        raise ValueError('Only read-only SELECT queries are allowed.')
    # pglast represents nodes as dictionaries with an @ node type.
    for key, node in walk(tree):
        if key == '@' and (node.endswith('Stmt') and node != 'SelectStmt'):
            raise ValueError('Only read-only SELECT queries are allowed, including inside CTEs.')
        if key == 'intoClause' and node:
            raise ValueError('SELECT INTO is not allowed.')
        if key == 'lockingClause' and node:
            raise ValueError('Row locking is not allowed.')
        if key == '@' and node == 'RangeVar':
            pass
        if key == 'schemaname' and node and node != 'public':
            raise ValueError('Only the public ERP schema is available.')
    def inspect_nodes(value):
        if isinstance(value, dict):
            if value.get('@') == 'FuncCall':
                names = [n.get('sval') for n in value.get('funcname', ())]
                if len(names) != 1 or names[0] not in PURE_FUNCTIONS:
                    raise ValueError('This function is not approved for read-only analysis.')
            for item in value.values():
                inspect_nodes(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                inspect_nodes(item)
    inspect_nodes(tree)
    def check_relations(value, visible=frozenset()):
        if isinstance(value, dict):
            scope = set(visible)
            if value.get('@') == 'SelectStmt' and value.get('withClause'):
                clause = value['withClause']
                ctes = clause.get('ctes', ())
                if clause.get('recursive'):
                    scope.update(cte['ctename'] for cte in ctes)
                for cte in ctes:
                    check_relations(cte['ctequery'], frozenset(scope))
                    scope.add(cte['ctename'])
            if value.get('@') == 'RangeVar':
                if value.get('catalogname'):
                    raise ValueError('Cross-database relations are unavailable.')
                if value['relname'] not in ERP_TABLES and not (not value.get('schemaname') and value['relname'] in scope):
                    raise ValueError('Only ERP tables are available for ordinary analysis.')
            if value.get('@') == 'TypeName':
                names = [n.get('sval') for n in value.get('names', ())]
                allowed_types = {'int2','int4','int8','integer','bigint','smallint','numeric','decimal','float4','float8','real','double precision','text','varchar','bpchar','bool','boolean','date','timestamp','timestamptz','time','interval'}
                if not names or names[-1] not in allowed_types or (len(names)>1 and names[0]!='pg_catalog'):
                    raise ValueError('Only built-in scalar casts are allowed.')
            for key, item in value.items():
                if key != 'withClause':
                    check_relations(item, frozenset(scope))
        elif isinstance(value, (tuple, list)):
            for item in value:
                check_relations(item, visible)
    check_relations(tree)
    from pglast.stream import RawStream
    return RawStream()(statements[0].stmt)

@contextmanager
def readonly_connection():
    with db.engines.get('readonly', db.engine).connect() as conn:
        with conn.begin():
            conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            conn.execute(text("SELECT set_config('statement_timeout', :timeout, true)"), {'timeout': str(current_app.config['QUERY_TIMEOUT_MS'])})
            conn.execute(text("SET LOCAL lock_timeout = '2s'"))
            conn.execute(text('SET LOCAL search_path TO pg_catalog, public'))
            yield conn
