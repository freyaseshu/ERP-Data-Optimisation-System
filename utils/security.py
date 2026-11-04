import hashlib
import hmac
import secrets
from urllib.parse import urlsplit
from flask import current_app, g
from sqlalchemy import text
from utils.db import db


def validate_production_config(config):
    if config['APP_ENV'] not in ('development', 'production'):
        raise ValueError('APP_ENV must be development or production.')
    if config['APP_ENV'] != 'production':
        return
    key = config.get('SECRET_KEY', '')
    if not isinstance(key, str) or len(key) < 32 or any(word in key.lower() for word in ('replace', 'your-own', 'change-me')):
        raise ValueError('Production requires an explicit random SECRET_KEY of at least 32 characters.')
    if not config.get('SECRET_KEY_CONFIGURED', True):
        raise ValueError('Production requires an explicit SECRET_KEY; a generated development key is not allowed.')
    url = urlsplit(config.get('PUBLIC_BASE_URL', ''))
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment:
        raise ValueError('Production requires PUBLIC_BASE_URL=https://your-host with no path or credentials.')
    if not config.get('SESSION_COOKIE_SECURE') or not config.get('WTF_CSRF_ENABLED', True):
        raise ValueError('Production requires Secure cookies and CSRF protection.')
    if not config.get('SQLALCHEMY_BINDS', {}).get('readonly'):
        raise ValueError('Production requires a separate READONLY_DATABASE_URL.')
    config['TRUSTED_HOSTS'] = [url.hostname, 'localhost', '127.0.0.1']


def csp_nonce():
    if 'csp_nonce' not in g:
        g.csp_nonce = secrets.token_urlsafe(24)
    return g.csp_nonce


def login_bucket(kind, value):
    return hmac.new(current_app.config['SECRET_KEY'].encode(), (kind + ':' + value).encode(), hashlib.sha256).hexdigest()


def consume_login_attempt(username, address):
    """Atomic PostgreSQL counters work across threads and server processes."""
    limits = [(login_bucket('address', address or 'unknown'), current_app.config['LOGIN_IP_RATE_LIMIT']),
              (login_bucket('account', username.casefold()), current_app.config['LOGIN_RATE_LIMIT'])]
    allowed = True
    with db.engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL statement_timeout = '3s'")
        conn.exec_driver_sql("SET LOCAL lock_timeout = '1s'")
        conn.exec_driver_sql("DELETE FROM login_throttles WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day'")
        for bucket, limit in limits:
            attempts = conn.execute(text('INSERT INTO login_throttles (bucket, attempts, expires_at) '
                "VALUES (:bucket, 1, CURRENT_TIMESTAMP + :seconds * INTERVAL '1 second') "
                'ON CONFLICT (bucket) DO UPDATE SET '
                'attempts=CASE WHEN login_throttles.expires_at <= CURRENT_TIMESTAMP THEN 1 ELSE login_throttles.attempts+1 END, '
                "expires_at=CASE WHEN login_throttles.expires_at <= CURRENT_TIMESTAMP THEN CURRENT_TIMESTAMP + :seconds * INTERVAL '1 second' ELSE login_throttles.expires_at END "
                'RETURNING attempts'), {'bucket': bucket, 'seconds': current_app.config['LOGIN_RATE_WINDOW_SECONDS']}).scalar_one()
            allowed = allowed and attempts <= limit
            if not allowed:
                break
    return allowed


def clear_account_throttle(username):
    with db.engine.begin() as conn:
        conn.execute(text('DELETE FROM login_throttles WHERE bucket=:bucket'), {'bucket': login_bucket('account', username.casefold())})
