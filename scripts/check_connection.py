import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from utils.db import db
if __name__=='__main__':
    try:
        with create_app().app_context():
            for name,engine in db.engines.items():
                with engine.connect() as conn:
                    print(name or 'primary',conn.exec_driver_sql('SELECT version()').scalar())
    except Exception:
        print('Connection failed. Check PostgreSQL status and .env. No passwords were guessed.')
        sys.exit(1)
