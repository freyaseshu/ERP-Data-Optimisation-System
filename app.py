from flask import Flask
from config import Config
from models.user import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    with app.app_context():
        # Imports are here to avoid circular dependencies
        from routes.auth_routes import auth_bp
        from routes.dashboard_routes import dashboard_bp
        from routes.analyser_routes import analyser_bp
        from routes.optimiser_routes import optimiser_bp
        # from routes.duplicate_routes import duplicate_bp
        # from routes.archive_routes import archive_bp
        # from routes.report_routes import report_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(analyser_bp)
        app.register_blueprint(optimiser_bp)
        # app.register_blueprint(duplicate_bp)
        # app.register_blueprint(archive_bp)
        # app.register_blueprint(report_bp)
        
        # Create tables if they don't exist
        # db.create_all()
        pass

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
