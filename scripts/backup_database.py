"""Create a private backup; optionally restore ONLY into a new disposable DB."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from config import Config
from utils.query_safety import ERP_TABLES

ROOT = Path(__file__).resolve().parents[1]


def executable(name, pg_bin=None):
    suffix = '.exe' if os.name == 'nt' else ''
    if pg_bin:
        candidate = Path(pg_bin) / (name + suffix)
    else:
        candidate = ROOT / '.local' / 'pgsql' / 'bin' / (name + suffix)
        if not candidate.is_file():
            located = shutil.which(name)
            if not located:
                raise ValueError('PostgreSQL tools missing. Supply --pg-bin with the matching server bin directory.')
            candidate = Path(located)
    if not candidate.is_file():
        raise ValueError('PostgreSQL executable not found.')
    return str(candidate)


def pg_run(tool, url, arguments):
    environment = os.environ.copy()
    if url.password:
        environment['PGPASSWORD'] = url.password
    dsn = url.set(drivername='postgresql', password=None).render_as_string(hide_password=False)
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    subprocess.run([tool, '--dbname', dsn, *arguments], env=environment, capture_output=True,
                   check=True, creationflags=flags)


def restore_check(backup, pg_bin=None):
    # No destination argument is accepted: never restore over demo/production data.
    name = 'erp_restore_' + uuid.uuid4().hex[:16]
    assert re.fullmatch(r'erp_restore_[0-9a-f]{16}', name)
    url = make_url(Config.SQLALCHEMY_DATABASE_URI)
    admin = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    created = False
    try:
        with admin.connect() as conn:
            conn.exec_driver_sql('CREATE DATABASE ' + name)
            created = True
        pg_run(executable('pg_restore', pg_bin), url.set(database=name),
               ['--clean', '--if-exists', '--no-owner', '--no-privileges', '--exit-on-error', str(backup)])
        from app import create_app
        from scripts.validate_dataset import validate_dataset
        from services.deployment_service import schema_ready
        from utils.db import db
        class Restored(Config):
            APP_ENV = 'development'
            SQLALCHEMY_BINDS = {}
            SQLALCHEMY_DATABASE_URI = url.set(database=name).render_as_string(hide_password=False)
        app = create_app(Restored)
        try:
            with app.app_context():
                with db.engine.connect() as conn:
                    schema_ready(conn)
                result = validate_dataset()
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        if not result['success']:
            raise ValueError('Restored dataset integrity validation failed.')
        return {'success': True, 'total_erp_records': result['total_erp_records'], 'checks': result['checks'], 'disposable_database_removed': True}
    finally:
        if created:
            with admin.connect() as conn:
                conn.exec_driver_sql('DROP DATABASE ' + name + ' WITH (FORCE)')
        admin.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--pg-bin', type=Path)
    parser.add_argument('--verify-restore', action='store_true', help='Requires CREATEDB; restores into a generated database and removes only that database.')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target = (args.output or ROOT / '.local' / 'backups' / f'erp-{stamp}-{uuid.uuid4().hex[:6]}.dump').resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Backup destination already exists; it was not overwritten.')
    pg_run(executable('pg_dump', args.pg_bin), make_url(Config.SQLALCHEMY_DATABASE_URI),
           ['--format=custom', '--no-owner', '--no-privileges', '--file', str(target)])
    result = {'success': True, 'backup': str(target), 'bytes': target.stat().st_size,
              'note': 'Data/schema backup only. Keep role grants, credentials, and server configuration separately; files are private and not encrypted by this script.'}
    if args.verify_restore:
        result['restore_rehearsal'] = restore_check(target, args.pg_bin)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'success': False, 'error': str(exc) if isinstance(exc, ValueError) else 'Backup or disposable restore failed. Check PostgreSQL tools, role permissions and private configuration.'}))
        sys.exit(1)
