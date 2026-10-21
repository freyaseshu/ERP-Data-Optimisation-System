import pytest
from services.query_analyser import QueryAnalyserService
from utils.query_safety import validate

@pytest.mark.parametrize('query', [
    'SELECT id, name FROM customers',
    "SELECT 'DROP TABLE; DELETE' AS text FROM customers LIMIT 1;",
    'WITH c AS (SELECT id FROM customers) SELECT * FROM c',
    'SELECT COUNT(*) FROM orders',
    'SELECT id::text FROM products',
    "SELECT * FROM customers WHERE city = 'Chicago'; -- trailing comment",
])
def test_allow_readonly(query):
    assert QueryAnalyserService.is_safe_query(query)[0]

@pytest.mark.parametrize('query', [
    None, '', 1, 'DROP TABLE customers', 'DELETE FROM orders', 'UPDATE products SET unit_price=0',
    'TRUNCATE orders', 'SELECT 1; DROP TABLE orders', 'SELECT 1;; SELECT 2',
    'SELECT * INTO new_table FROM customers', 'SELECT * FROM orders FOR UPDATE',
    'WITH x AS (DELETE FROM customers RETURNING *) SELECT * FROM x',
    'SELECT pg_sleep(99)', "SELECT pg_read_file('/secret')",
    "SELECT set_config('transaction_read_only','off',true)",
    "SELECT nextval('users_id_seq')", 'SELECT * FROM users', 'SELECT password FROM public.users',
    'SELECT * FROM pg_catalog.pg_authid', 'SELECT * FROM information_schema.tables',
    'WITH users AS (SELECT * FROM users) SELECT * FROM users',
    'WITH users AS (SELECT * FROM public.users) SELECT * FROM users',
    'SELECT public.sum(amount) FROM payments', 'SELECT 1::public.secret_type',
    'EXPLAIN ANALYZE DELETE FROM customers', 'SELECT * FROM missing_secret_table',
])
def test_reject_unsafe(query):
    assert not QueryAnalyserService.is_safe_query(query)[0]

@pytest.mark.parametrize('url', ['/api/analyse-query','/api/optimise-query','/api/benchmarks/run','/api/execute-query'])
def test_authentication_required(client,url):
    assert client.post(url,json={'query':'SELECT 1'}).status_code==401

@pytest.mark.parametrize('url', ['/api/apply-optimization','/api/benchmarks/run','/api/duplicates/delete','/api/archive/execute'])
def test_analyst_cannot_mutate(analyst_client,url):
    assert analyst_client.post(url,json={'confirm':True}).status_code==403

def test_missing_or_invalid_json(admin_client):
    for body in ['{}', '[]', 'null', '{bad']:
        response=admin_client.post('/api/analyse-query',data=body,content_type='application/json')
        assert response.status_code==400

def test_cross_site_mutation(admin_client):
    assert admin_client.post('/api/analyse-query',json={'query':'SELECT 1'},headers={'Sec-Fetch-Site':'cross-site'}).status_code==403

def test_no_password_bypass(client):
    response=client.post('/login',data={'username':'admin','password':'password'})
    assert 'Invalid username or password' in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert 'user_id' not in session

def test_readonly_enforced_in_database(app):
    from utils.query_safety import readonly_connection
    from sqlalchemy.exc import DBAPIError
    with app.app_context():
        with pytest.raises(DBAPIError):
            with readonly_connection() as conn:
                conn.exec_driver_sql('DELETE FROM customers WHERE false')

def test_no_unrestricted_ddl(admin_client):
    response=admin_client.post('/api/apply-optimization',json={'optimization_sql':'CREATE INDEX x ON customers (city); DROP TABLE orders;', 'original_query':'SELECT * FROM customers', 'confirm':True})
    assert response.status_code==400

def test_invalid_query_never_executes(admin_client,app):
    from utils.db import db
    with app.app_context():
        before=db.session.execute(db.text('SELECT count(*) FROM customers')).scalar()
    assert admin_client.post('/api/optimise-query',json={'query':'DELETE FROM customers'}).status_code==400
    with app.app_context():
        assert db.session.execute(db.text('SELECT count(*) FROM customers')).scalar()==before

def test_statement_timeout_and_recovery(app,monkeypatch):
    monkeypatch.setitem(app.config,'QUERY_TIMEOUT_MS',1)
    with app.app_context():
        result=QueryAnalyserService.analyze_query('SELECT count(*) FROM customers a CROSS JOIN customers b CROSS JOIN customers c',run_analyze=True)
        assert result['success'] is False
        assert 'timeout' in result['error']
    monkeypatch.setitem(app.config,'QUERY_TIMEOUT_MS',5000)
    with app.app_context():
        assert QueryAnalyserService.analyze_query('SELECT id FROM customers LIMIT 1')['success']
