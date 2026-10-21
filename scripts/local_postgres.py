"""Manage the optional project-local PostgreSQL cluster (Windows, no service install)."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
BIN = LOCAL / 'pgsql' / 'bin'
DATA = LOCAL / 'pgdata'

def invoke(args):
    return subprocess.run([str(a) for a in args], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

def main(action):
    if not (BIN / 'pg_ctl.exe').exists():
        raise RuntimeError('PostgreSQL binaries missing; install PostgreSQL or extract official EDB Windows binaries to .local/pgsql.')
    if action == 'init':
        if (ROOT / '.env').exists() or (DATA / 'PG_VERSION').exists():
            raise RuntimeError('Existing .env or cluster preserved. Use start; configure external PostgreSQL manually if needed.')
        LOCAL.mkdir(exist_ok=True)
        db_password = secrets.token_urlsafe(32)
        password_file = LOCAL / 'db-password.txt'
        password_file.write_text(db_password, encoding='utf-8')
        invoke([BIN / 'initdb.exe', '-D', DATA, '-U', 'erp_local', '-A', 'scram-sha-256', '--pwfile', password_file, '--encoding=UTF8', '--locale=C'])
        (ROOT / '.env').write_text('DATABASE_URL=postgresql+psycopg://erp_local:' + db_password + '@127.0.0.1:55432/erp_optimisation_db\nSECRET_KEY=' + secrets.token_hex(32) + '\n', encoding='utf-8')
        password_file.unlink()
        admin_password = secrets.token_urlsafe(15)
        (LOCAL / 'login.txt').write_text('Local website: http://127.0.0.1:5000\nUsername: admin\nPassword: ' + admin_password + '\n', encoding='utf-8')
        start()
        from scripts.init_db import initialise
        # config is imported after .env has been created.
        initialise(create_database=True)
        from app import create_app
        from scripts.generate_dataset import seed_user
        with create_app().app_context():
            seed_user('admin', admin_password, 'Admin')
        print('Database initialised. Local website login saved to .local/login.txt (keep private).')
    elif action == 'start':
        start()
    elif action == 'stop':
        invoke([BIN / 'pg_ctl.exe', '-D', DATA, '-m', 'fast', '-w', 'stop'])
    elif action == 'status':
        if running_cluster():
            print('Project-local PostgreSQL verified at 127.0.0.1:55432.')
        else:
            invoke([BIN / 'pg_ctl.exe', '-D', DATA, 'status'])

def running_cluster():
    # pg_ctl's OS-process check can be denied under a restricted shell, even
    # while PostgreSQL is healthy. Verify the actual server and its data folder.
    from dotenv import dotenv_values
    from sqlalchemy.engine import make_url
    import psycopg
    values=dotenv_values(ROOT / '.env')
    uri=values.get('DATABASE_URL')
    if not uri:
        return False
    url=make_url(uri)
    if url.host not in ('localhost','127.0.0.1') or url.port != 55432:
        return False
    try:
        with psycopg.connect(url.set(drivername='postgresql',database='postgres').render_as_string(hide_password=False),connect_timeout=3) as conn:
            directory=conn.execute('SHOW data_directory').fetchone()[0]
            if Path(directory).resolve()!=DATA.resolve():
                raise RuntimeError('Port 55432 belongs to a different PostgreSQL cluster; existing data was not changed.')
            return True
    except psycopg.OperationalError:
        return False

def start():
    if running_cluster():
        print('Project-local PostgreSQL connection and data directory verified; already running.')
        return
    status = subprocess.run([str(BIN / 'pg_ctl.exe'), '-D', str(DATA), 'status'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if status.returncode == 0:
        print('Project-local PostgreSQL is already running.')
        return
    invoke([BIN / 'pg_ctl.exe', '-D', DATA, '-l', LOCAL / 'postgres.log', '-o', '-h 127.0.0.1 -p 55432', '-w', 'start'])

if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['init', 'start', 'stop', 'status'])
    main(parser.parse_args().action)
