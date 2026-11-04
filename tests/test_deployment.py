import re
import secrets
import uuid
from datetime import timedelta
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from psycopg import sql
from app import create_app
from config import Config
from utils.db import db
from utils.security import validate_production_config, login_bucket
from services.deployment_service import deployment_checks


def token(response):
    return re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))[1]


@pytest.mark.parametrize('path', ['/health/live', '/health/ready'])
def test_health_without_authentication(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert 'database' not in response.json and 'version' not in response.json


def test_readiness_failure_is_safe(client, monkeypatch):
    import services.deployment_service as service
    monkeypatch.setattr(service, 'schema_ready', lambda conn: (_ for _ in ()).throw(RuntimeError('private database detail')))
    response = client.get('/health/ready')
    assert response.status_code == 503 and response.json == {'status': 'unavailable'}
    assert client.get('/health/live').status_code == 200


@pytest.mark.parametrize('override', [
    {'SECRET_KEY': 'short'}, {'SECRET_KEY': 'replace-with-a-random-secret-12345678'},
    {'SECRET_KEY_CONFIGURED': False}, {'PUBLIC_BASE_URL': 'http://erp.test'},
    {'PUBLIC_BASE_URL': 'https://user:password@erp.test'}, {'PUBLIC_BASE_URL': 'https://erp.test/subpath'},
    {'PUBLIC_BASE_URL': ''}, {'SESSION_COOKIE_SECURE': False}, {'WTF_CSRF_ENABLED': False},
    {'SQLALCHEMY_BINDS': {}}, {'APP_ENV': 'typo'},
])
def test_production_rejects_unsafe_configuration(override):
    settings = {'APP_ENV': 'production', 'SECRET_KEY': 'a' * 64, 'SECRET_KEY_CONFIGURED': True,
                'PUBLIC_BASE_URL': 'https://erp.test', 'SESSION_COOKIE_SECURE': True,
                'SQLALCHEMY_BINDS': {'readonly': 'postgresql+psycopg://unused'}, 'WTF_CSRF_ENABLED': True}
    settings.update(override)
    with pytest.raises(ValueError):
        validate_production_config(settings)


def test_csrf_login_api_and_logout(app, client, monkeypatch):
    monkeypatch.setitem(app.config, 'WTF_CSRF_ENABLED', True)
    assert client.post('/login', data={'username': 'admin', 'password': 'test-admin-only-password'}).status_code == 400
    csrf = token(client.get('/login'))
    assert client.post('/login', data={'username': 'admin', 'password': 'test-admin-only-password', 'csrf_token': csrf}).status_code == 302
    csrf = token(client.get('/dashboard'))
    assert client.post('/api/analyse-query', json={'query': 'SELECT 1'}).status_code == 400
    assert client.post('/api/analyse-query', json={'query': 'SELECT 1'}, headers={'X-CSRFToken': 'wrong'}).status_code == 400
    assert client.post('/api/analyse-query', json={'query': 'SELECT 1'}, headers={'X-CSRFToken': csrf}).status_code == 200
    assert client.post('/api/analyse-query', json={'query': 'SELECT 1'}, headers={'X-CSRFToken': csrf, 'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.get('/logout').status_code == 405
    assert client.post('/logout').status_code == 400
    assert client.post('/logout', data={'csrf_token': csrf}).status_code == 302
    assert client.get('/api/dashboard/stats').status_code == 401


def test_login_throttle_expiry_and_private_keys(app, client, monkeypatch):
    monkeypatch.setitem(app.config, 'LOGIN_RATE_LIMIT', 2)
    username = 'invalid-' + uuid.uuid4().hex[:12]
    for _ in range(2):
        assert client.post('/login', data={'username': username, 'password': 'wrong'}).status_code == 200
    limited = client.post('/login', data={'username': username, 'password': 'wrong'})
    assert limited.status_code == 429 and limited.headers['Retry-After'] == '600'
    with app.app_context(), db.engine.begin() as conn:
        bucket = login_bucket('account', username)
        conn.execute(text("UPDATE login_throttles SET expires_at=CURRENT_TIMESTAMP-INTERVAL '1 second' WHERE bucket=:bucket"), {'bucket': bucket})
        assert username not in bucket and len(bucket) == 64
    assert client.post('/login', data={'username': username, 'password': 'wrong'}).status_code == 200


def test_ip_throttle_does_not_depend_on_username(app, client, monkeypatch):
    monkeypatch.setitem(app.config, 'LOGIN_IP_RATE_LIMIT', 2)
    address = '198.51.100.' + str(100 + secrets.randbelow(100))
    for i in range(2):
        assert client.post('/login', data={'username': f'ip-attempt-{i}', 'password': 'wrong'}, environ_overrides={'REMOTE_ADDR': address}).status_code == 200
    assert client.post('/login', data={'username': 'different-account', 'password': 'wrong'}, environ_overrides={'REMOTE_ADDR': address}).status_code == 429


def test_deleted_account_session_is_revoked(admin_client):
    with admin_client.session_transaction() as session:
        session['user_id'] = -999999
    assert admin_client.get('/api/explorer/tables').status_code == 401
    assert admin_client.get('/dashboard').status_code == 302


def test_session_expiration(app, admin_client, monkeypatch):
    monkeypatch.setitem(app.config, 'PERMANENT_SESSION_LIFETIME', timedelta(seconds=-1))
    assert admin_client.get('/api/dashboard/stats').status_code == 401


def test_headers_and_nonce_markup(admin_client):
    first = admin_client.get('/explorer')
    html = first.get_data(as_text=True)
    nonce = re.search(r'<script nonce="([^"]+)"', html)[1]
    assert "'nonce-" + nonce + "'" in first.headers['Content-Security-Policy']
    assert 'onclick=' not in html and 'onkeyup=' not in html
    assert first.headers['Cache-Control'] == 'no-store'
    assert first.headers['X-Frame-Options'] == 'DENY'
    assert first.headers['X-Request-ID']
    second = admin_client.get('/benchmarks')
    assert nonce not in second.headers['Content-Security-Policy']
    assert not re.search(r'<[^>]+\son\w+=', second.get_data(as_text=True))


def test_json_error_and_report_bounds(app, admin_client, monkeypatch):
    assert admin_client.get('/api/missing-route').status_code == 404
    assert admin_client.get('/api/missing-route').json['success'] is False
    assert admin_client.get('/api/reports/performance?range=custom&start=2025-01-01T00:00:00&end=2025-01-02').status_code == 400
    monkeypatch.setitem(app.config, 'REPORT_ROW_LIMIT', 1)
    for _ in range(2):
        assert admin_client.post('/api/analyse-query', json={'query': 'SELECT 1', 'run_analyze': True}).status_code == 200
    result = admin_client.get('/api/reports/performance?range=all').json['data']
    assert result['truncated'] is True and len(result['all_logs']) == result['row_limit'] == 1


def test_server_does_not_expose_internal_exception(admin_client, monkeypatch):
    from services.query_analyser import QueryAnalyserService
    def failure(*args, **kwargs):
        raise RuntimeError('private-password-should-not-escape')
    monkeypatch.setattr(QueryAnalyserService, 'execute_query', failure)
    response = admin_client.post('/api/execute-query', json={'query': 'SELECT 1'})
    assert response.status_code == 500 and response.json['success'] is False
    assert 'private-password' not in response.get_data(as_text=True)
    assert response.headers['X-Request-ID']


def test_server_options_refuse_wildcard_proxy(monkeypatch):
    from serve import server_options
    monkeypatch.setenv('ERP_TRUSTED_PROXY', '*')
    with pytest.raises(ValueError):
        server_options()
    monkeypatch.setenv('ERP_TRUSTED_PROXY', '127.0.0.1')
    options = server_options()
    assert options['trusted_proxy_count'] == 1 and not options['expose_tracebacks']


def test_recommendation_status_and_index_commit_atomically(app, admin_client):
    from sqlalchemy import event
    from models.optimisation_recommendation import OptimisationRecommendation
    with app.app_context():
        recommendation = OptimisationRecommendation(query_text='SELECT id FROM employees WHERE salary>50000', recommendation_type='INDEX',
            title='Atomic index test', description='Failure injection', status='Pending',
            sql_statement='CREATE INDEX IF NOT EXISTS idx_release_atomic ON employees (salary);')
        db.session.add(recommendation)
        db.session.commit()
        rec_id = recommendation.id
        count = db.session.execute(text('SELECT count(*) FROM query_performance_logs')).scalar()
        engine = db.engine
    def reject_final_status(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('UPDATE optimisation_recommendations') and parameters.get('status') == 'Applied':
            raise RuntimeError('Injected status persistence failure')
    event.listen(engine, 'before_cursor_execute', reject_final_status)
    try:
        response = admin_client.post('/api/apply-optimization', json={'recommendation_id': rec_id, 'confirm': True})
        assert response.status_code == 400, response.json
    finally:
        event.remove(engine, 'before_cursor_execute', reject_final_status)
    with app.app_context(), db.engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT to_regclass('public.idx_release_atomic')").scalar() is None
        assert conn.execute(text('SELECT status FROM optimisation_recommendations WHERE id=:id'), {'id': rec_id}).scalar() == 'Unsuccessful'
        assert conn.exec_driver_sql('SELECT count(*) FROM query_performance_logs').scalar() == count


@pytest.fixture(scope='module')
def production_app(app):
    """Exercise real restricted roles in a fresh database, never the demo DB."""
    suffix = uuid.uuid4().hex[:10]
    name, owner, reader = ['erp_release_' + prefix + suffix for prefix in ('db_', 'app_', 'reader_')]
    owner_password, reader_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    base = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        if not conn.exec_driver_sql('SELECT rolsuper FROM pg_roles WHERE rolname=current_user').scalar():
            admin.dispose()
            pytest.skip('Restricted-role deployment rehearsal requires a local test superuser.')
        cursor = conn.connection.driver_connection.cursor()
        for role, password in ((owner, owner_password), (reader, reader_password)):
            cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier(role), sql.Literal(password)))
        cursor.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(name), sql.Identifier(owner)))
        cursor.execute(sql.SQL('ALTER ROLE {} SET default_transaction_read_only=on').format(sql.Identifier(reader)))
        cursor.close()
    class Production(Config):
        TESTING = True
        APP_ENV = 'production'
        SECRET_KEY = secrets.token_hex(32)
        SECRET_KEY_CONFIGURED = True
        SESSION_COOKIE_SECURE = True
        PUBLIC_BASE_URL = 'https://erp.example.test'
        SQLALCHEMY_DATABASE_URI = base.set(database=name, username=owner, password=owner_password).render_as_string(hide_password=False)
        SQLALCHEMY_BINDS = {'readonly': base.set(database=name, username=reader, password=reader_password).render_as_string(hide_password=False)}
    application = create_app(Production)
    try:
        with application.app_context():
            from scripts.generate_dataset import seed_user
            from utils.query_safety import ERP_TABLES
            db.create_all()
            seed_user('release-admin', 'release-test-password-only', 'Admin')
            with db.engine.begin() as conn:
                cursor = conn.connection.driver_connection.cursor()
                cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(reader)))
                for table in ERP_TABLES:
                    cursor.execute(sql.SQL('GRANT SELECT ON public.{} TO {}').format(sql.Identifier(table), sql.Identifier(reader)))
                cursor.close()
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            for engine in db.engines.values():
                engine.dispose()
        assert all(value.startswith('erp_release_') and value.endswith(suffix) for value in (name, owner, reader))
        with admin.connect() as conn:
            cursor = conn.connection.driver_connection.cursor()
            cursor.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
            for role in (reader, owner):
                cursor.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
            cursor.close()
        admin.dispose()


def test_production_rehearsal_with_restricted_roles(production_app):
    with production_app.app_context():
        checks = deployment_checks()
        assert checks['success'], checks
    with production_app.test_client() as client:
        base = 'https://erp.example.test'
        assert client.get('/health/ready', base_url=base).status_code == 200
        assert client.get('/health/live', base_url='https://attacker.invalid').status_code == 400
        page = client.get('/login', base_url=base)
        response = client.post('/login', base_url=base, data={'username': 'release-admin', 'password': 'release-test-password-only', 'csrf_token': token(page)}, headers={'Referer': base + '/login'})
        assert response.status_code == 302
        assert 'Secure' in response.headers['Set-Cookie'] and 'HttpOnly' in response.headers['Set-Cookie']
        csrf = token(client.get('/dashboard', base_url=base))
        assert client.post('/api/analyse-query', base_url=base, json={'query': 'SELECT 1'}, headers={'X-CSRFToken': csrf, 'Referer': base + '/analyser'}).status_code == 200
        assert 'max-age=' in page.headers['Strict-Transport-Security']
