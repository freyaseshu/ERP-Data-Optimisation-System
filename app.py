from flask import Flask, jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError
from config import Config
from utils.db import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://'):
        raise ValueError('DATABASE_URL must use postgresql+psycopg://')
    db.init_app(app)
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
    for blueprint in (auth_bp, dashboard_bp, analyser_bp, optimiser_bp, explorer_bp, benchmark_bp, limitations_bp, report_bp, duplicate_bp, archive_bp):
        app.register_blueprint(blueprint)

    @app.before_request
    def protect_mutations():
        # JSON requests cannot be submitted by cross-origin HTML forms. No CORS is enabled.
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and request.path.startswith('/api/'):
            if not request.is_json or not isinstance(request.get_json(silent=True), dict):
                return jsonify(success=False, error='A JSON object is required.'), 400
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                return jsonify(success=False, error='Cross-site request rejected.'), 403

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.warning('Database operation failed (%s)', type(error).__name__)
        message = 'PostgreSQL is unavailable or the schema needs initialising. Check .env and run setup.ps1.'
        if request.path.startswith('/api/'):
            return jsonify(success=False, error=message, message=message), 503
        return render_template('error.html', message=message), 503

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False)
