import uuid
from flask import Flask, jsonify, render_template, request, session, g, redirect, url_for
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException, SecurityError
from sqlalchemy.exc import SQLAlchemyError
from config import Config
from utils.db import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    from utils.security import validate_production_config, csp_nonce
    validate_production_config(app.config)
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://'):
        raise ValueError('DATABASE_URL must use postgresql+psycopg://')
    db.init_app(app)
    @app.before_request
    def start_request():
        g.request_id = uuid.uuid4().hex

    CSRFProtect(app)
    app.jinja_env.globals['csp_nonce'] = csp_nonce
    import models
    from routes.auth_routes import auth_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.analyser_routes import analyser_bp
    from routes.optimiser_routes import optimiser_bp
    from routes.explorer_routes import explorer_bp
    from routes.benchmark_routes import benchmark_bp
    from routes.limitations_routes import limitations_bp
    from routes.report_routes import report_bp
    from routes.duplicate_routes import duplicate_bp
    from routes.archive_routes import archive_bp
    from routes.workspace_routes import workspace_bp
    for blueprint in (auth_bp, dashboard_bp, analyser_bp, optimiser_bp, explorer_bp, benchmark_bp, limitations_bp, report_bp, duplicate_bp, archive_bp, workspace_bp):
        app.register_blueprint(blueprint)

    @app.before_request
    def protect_mutations():
        # JSON requests cannot be submitted by cross-origin HTML forms. No CORS is enabled.
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and request.path.startswith('/api/'):
            if not request.is_json or not isinstance(request.get_json(silent=True), dict):
                return jsonify(success=False, error='A JSON object is required.'), 400
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                return jsonify(success=False, error='Cross-site request rejected.'), 403

    @app.before_request
    def validate_session_user():
        if session.get('user_id') and request.endpoint not in ('static', 'auth.login', 'auth.logout', 'health_live', 'health_ready'):
            from models.user import User
            user = db.session.get(User, session['user_id'])
            if user is None:
                session.clear()
                if request.path.startswith('/api/'):
                    return jsonify(success=False, error='Session account no longer exists. Sign in again.'), 401
                return redirect(url_for('auth.login'))
            g.current_user = user
            if session.get('role') != user.role:
                session['role'] = user.role

    @app.route('/health/live')
    def health_live():
        return jsonify(status='alive')

    @app.route('/health/ready')
    def health_ready():
        from services.deployment_service import readiness
        ok = readiness()
        return jsonify(status='ready' if ok else 'unavailable'), 200 if ok else 503

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = 'Security token missing or expired. Reload the page and try again.'
        if request.path.startswith('/api/'):
            return jsonify(success=False, error=message), 400
        return render_template('error.html', message=message), 400

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.warning('Database operation failed (%s)', type(error).__name__)
        message = 'PostgreSQL is unavailable or the schema needs initialising. Check .env and run setup.ps1.'
        if request.path.startswith('/api/'):
            if request.endpoint == 'dashboard.stats':
                return jsonify(success=False, error=message, message=message, stats={'db_connected': False}), 503
            return jsonify(success=False, error=message, message=message), 503
        return render_template('error.html', message=message), 503

    @app.errorhandler(Exception)
    def request_error(error):
        if isinstance(error, SecurityError):
            return jsonify(success=False, error='Untrusted Host header.'), 400
        status = error.code if isinstance(error, HTTPException) else 500
        message = error.description if isinstance(error, HTTPException) else 'Unexpected server error. Reference: ' + g.get('request_id', 'unknown')
        if status == 500:
            db.session.rollback()
            app.logger.error('Unhandled request failure (%s), request_id=%s', type(error).__name__, g.get('request_id', 'unknown'))
        if request.path.startswith('/api/'):
            return jsonify(success=False, error=message), status
        return render_template('error.html', message=message), status

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Request-ID'] = g.get('request_id', uuid.uuid4().hex)
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' 'nonce-" + csp_nonce() + "'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        if app.config['APP_ENV'] == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False)
