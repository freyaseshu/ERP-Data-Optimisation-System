"""Integration tests run ONLY in an automatically created disposable database."""
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app import create_app
from config import Config
from utils.db import db
from scripts.generate_dataset import generate_dataset, seed_user

@pytest.fixture(scope='session')
def app():
    base = make_url(Config.SQLALCHEMY_DATABASE_URI)
    test_name = 'erp_test_' + uuid.uuid4().hex[:12]
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as conn:
        conn.exec_driver_sql('CREATE DATABASE ' + test_name)
    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_BINDS = {}
        SECRET_KEY = 'test-only-session-key'
        SQLALCHEMY_DATABASE_URI = base.set(database=test_name).render_as_string(hide_password=False)
    application = create_app(TestConfig)
    try:
        with application.app_context():
            db.create_all()
            generate_dataset('medium')
            seed_user('admin', 'test-admin-only-password', 'Admin')
            seed_user('analyst', 'test-analyst-only-password', 'Analyst')
        yield application
    finally:
        with application.app_context():
            db.session.remove()
            db.engine.dispose()
        # test_name is generated locally with fixed safe prefix and hex suffix.
        assert test_name.startswith('erp_test_') and len(test_name)==21
        with admin.connect() as conn:
            conn.exec_driver_sql('DROP DATABASE ' + test_name + ' WITH (FORCE)')
        admin.dispose()

@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client

@pytest.fixture
def admin_client(client):
    response = client.post('/login', data={'username':'admin','password':'test-admin-only-password'})
    assert response.status_code == 302
    return client

@pytest.fixture
def analyst_client(client):
    response=client.post('/login',data={'username':'analyst','password':'test-analyst-only-password'})
    assert response.status_code==302
    return client

@pytest.fixture
def fresh_database():
    """A separate blank database for generator success and failure tests."""
    from contextlib import contextmanager
    @contextmanager
    def create():
        base=make_url(Config.SQLALCHEMY_DATABASE_URI)
        name='erp_test_'+uuid.uuid4().hex[:12]
        engine=create_engine(base.set(database='postgres'),isolation_level='AUTOCOMMIT')
        with engine.connect() as conn:conn.exec_driver_sql('CREATE DATABASE '+name)
        class Blank(Config):
            TESTING=True
            SQLALCHEMY_BINDS={}
            SQLALCHEMY_DATABASE_URI=base.set(database=name).render_as_string(hide_password=False)
        application=create_app(Blank)
        try:
            with application.app_context():
                db.create_all()
                yield application
        finally:
            with application.app_context():
                db.session.remove()
                db.engine.dispose()
            assert name.startswith('erp_test_') and len(name)==21
            with engine.connect() as conn:conn.exec_driver_sql('DROP DATABASE '+name+' WITH (FORCE)')
            engine.dispose()
    return create
