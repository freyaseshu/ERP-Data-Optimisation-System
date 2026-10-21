import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError
from utils.db import db
from utils.query_safety import ERP_TABLES

def test_postgres_schema_and_keys(app):
    with app.app_context(),db.engine.connect() as conn:
        assert 'PostgreSQL' in conn.exec_driver_sql('SELECT version()').scalar()
        catalog=inspect(conn)
        for table in ERP_TABLES:
            assert catalog.has_table(table)
            assert catalog.get_pk_constraint(table)['constrained_columns']==['id']
        assert catalog.get_foreign_keys('order_items')
        assert catalog.get_foreign_keys('orders')

def test_foreign_key_enforcement(app):
    with app.app_context():
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(text("INSERT INTO payments (order_id,payment_date,amount,payment_method,transaction_ref) VALUES (-999,now(),1,'Wire','test-invalid')"))

def test_check_constraint_enforcement(app):
    with app.app_context():
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(text('UPDATE inventory SET quantity_on_hand=-1 WHERE id=(SELECT min(id) FROM inventory)'))

def test_database_instance_is_shared():
    from models.user import db as user_db
    assert user_db is db

def test_no_engine_fallback():
    from app import create_app
    from config import Config
    class Invalid(Config):SQLALCHEMY_DATABASE_URI='sqlite://'
    with pytest.raises(ValueError):create_app(Invalid)
