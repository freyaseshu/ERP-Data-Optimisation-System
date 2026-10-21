import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql+psycopg://localhost:5432/erp_optimisation_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_size': 5, 'max_overflow': 5, 'pool_timeout': 10, 'connect_args': {'connect_timeout': 3}}
    SQLALCHEMY_BINDS = {'readonly': {'url': os.environ['READONLY_DATABASE_URL'], 'pool_pre_ping': True, 'pool_size': 3, 'max_overflow': 2, 'connect_args': {'connect_timeout': 3}}} if os.getenv('READONLY_DATABASE_URL') else {}
    QUERY_TIMEOUT_MS = int(os.getenv('QUERY_TIMEOUT_MS', '5000'))
    SLOW_QUERY_MS = float(os.getenv('SLOW_QUERY_MS', '100'))
    QUERY_RESULT_LIMIT = 100
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 65536
