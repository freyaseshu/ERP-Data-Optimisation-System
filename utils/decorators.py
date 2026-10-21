from functools import wraps
from flask import session, jsonify, redirect, url_for, request
from utils.db import db

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api/'):
                return jsonify(success=False, error='Authentication required', message='Authentication required'), 401
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            from models.user import User
            user = db.session.get(User, session['user_id'])
            if not user or user.role not in roles:
                return jsonify(success=False, error='Administrator permission required.'), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
