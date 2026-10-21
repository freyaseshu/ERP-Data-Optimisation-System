"""Optional one-time least-privilege reader provisioning by the database owner.
No existing role or saved reader configuration is overwritten.
"""
import hashlib
import os
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from psycopg import sql
from config import Config
from utils.query_safety import ERP_TABLES

def configure():
    root=Path(__file__).resolve().parents[1]
    env=root/'.env'
    if os.getenv('READONLY_DATABASE_URL') or 'READONLY_DATABASE_URL=' in env.read_text(encoding='utf-8'):
        print('Existing read-only connection configuration preserved.')
        return
    url=make_url(Config.SQLALCHEMY_DATABASE_URI)
    role='erp_reader_'+hashlib.sha256(url.database.encode()).hexdigest()[:10]
    password=secrets.token_urlsafe(32)
    engine=create_engine(url)
    with engine.begin() as conn:
        if conn.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'),{'role':role}).scalar():
            raise RuntimeError('Reader role already exists; configure its credentials manually. No role was changed.')
        raw=conn.connection.driver_connection
        with raw.cursor() as cur:
            cur.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role),sql.Literal(password)))
            cur.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(url.database),sql.Identifier(role)))
            cur.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
            for table in ERP_TABLES:
                cur.execute(sql.SQL('GRANT SELECT ON TABLE public.{} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
            cur.execute(sql.SQL('ALTER ROLE {} SET default_transaction_read_only = on').format(sql.Identifier(role)))
            cur.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '5s'").format(sql.Identifier(role)))
    reader_url=url.set(username=role,password=password).render_as_string(hide_password=False)
    with env.open('a',encoding='utf-8') as handle:
        handle.write('\nREADONLY_DATABASE_URL='+reader_url+'\n')
    print('Restricted reader role created; only SELECT on the ten ERP tables was granted. Restart Flask.')
    engine.dispose()
if __name__=='__main__':configure()
