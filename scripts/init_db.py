"""Create the configured PostgreSQL database and additive schema; never drop data."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url
from config import Config
from app import create_app
from utils.db import db

def initialise(create_database=False):
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    if create_database:
        engine = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT', connect_args={'connect_timeout': 3})
        with engine.connect() as conn:
            if not conn.execute(text('SELECT 1 FROM pg_database WHERE datname=:name'), {'name': url.database}).scalar():
                conn.exec_driver_sql('CREATE DATABASE ' + conn.dialect.identifier_preparer.quote(url.database))
        engine.dispose()
    app = create_app()
    with app.app_context():
        # Stop with a concrete mismatch instead of claiming create_all migrated existing tables.
        catalog = inspect(db.engine)
        mismatches = []
        for table in db.metadata.sorted_tables:
            if catalog.has_table(table.name):
                missing = set(table.columns.keys()) - {c['name'] for c in catalog.get_columns(table.name)}
                if missing:
                    mismatches.append(table.name + ': missing ' + ', '.join(sorted(missing)))
        if mismatches:
            raise RuntimeError('Existing schema needs a reviewed migration (no data changed): ' + '; '.join(mismatches))
        db.create_all()
        from models import _RULES
        with db.engine.begin() as conn:
            inspector = inspect(conn)
            for table, rules in _RULES.items():
                existing = {c['name'] for c in inspector.get_check_constraints(table)}
                for name, expression in rules:
                    if name not in existing:
                        conn.exec_driver_sql('ALTER TABLE ' + table + ' ADD CONSTRAINT ' + name + ' CHECK (' + expression + ')')
        print('PostgreSQL schema ready: ' + str(len(db.metadata.tables)) + ' tables. Existing data preserved.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-database', action='store_true')
    args = parser.parse_args()
    try:
        initialise(args.create_database)
    except Exception as exc:
        print('Initialisation failed (' + type(exc).__name__ + '). Check PostgreSQL, .env, privileges and existing schema.')
        if isinstance(exc, RuntimeError):
            print(str(exc))
        sys.exit(1)
