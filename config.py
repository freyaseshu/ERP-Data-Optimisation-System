import os
import secrets
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

ENV_FILE = Path(os.getenv('ERP_ENV_FILE', str(Path(__file__).parent / '.env'))).resolve()
load_dotenv(ENV_FILE)

class Config:
    APP_ENV = os.getenv('APP_ENV', 'development')
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SECRET_KEY_CONFIGURED = bool(os.getenv('SECRET_KEY'))
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql+psycopg://localhost:5432/erp_optimisation_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_size': 5, 'max_overflow': 5, 'pool_timeout': 10, 'connect_args': {'connect_timeout': 3, 'options': '-c statement_timeout=30000 -c lock_timeout=2000'}}
    SQLALCHEMY_BINDS = {'readonly': {'url': os.environ['READONLY_DATABASE_URL'], 'pool_pre_ping': True, 'pool_size': 3, 'max_overflow': 2, 'connect_args': {'connect_timeout': 3}}} if os.getenv('READONLY_DATABASE_URL') else {}
    QUERY_TIMEOUT_MS = int(os.getenv('QUERY_TIMEOUT_MS', '5000'))
    SLOW_QUERY_MS = float(os.getenv('SLOW_QUERY_MS', '100'))
    QUERY_RESULT_LIMIT = 100
    REPORT_ROW_LIMIT = 1000
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 65536
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '')
    SESSION_COOKIE_SECURE = APP_ENV == 'production'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = False
    WTF_CSRF_TIME_LIMIT = 3600
    LOGIN_RATE_LIMIT = 10
    LOGIN_IP_RATE_LIMIT = 50
    LOGIN_RATE_WINDOW_SECONDS = 600
