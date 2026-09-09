"""
Auth/role decorators used by protected routes.
"""
from functools import wraps
from flask import session, jsonify, redirect, url_for, request


def login_required(view_func):
    """Blocks access unless a user is logged in (session-based)."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "message": "Authentication required",
                    "data": {}
                }), 401
            return redirect(url_for('auth.login_page'))
        return view_func(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Restrict a route to one or more roles, e.g. @role_required('Admin')."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                    return jsonify({"success": False, "message": "Authentication required", "data": {}}), 401
                return redirect(url_for('auth.login_page'))
            if session.get('role') not in roles:
                if request.path.startswith('/api/'):
                    return jsonify({"success": False, "message": "Insufficient permissions", "data": {}}), 403
                return redirect(url_for('dashboard.dashboard_page'))
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
