from datetime import datetime, timezone
from flask import Blueprint, render_template, jsonify, current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.db import db
from utils.decorators import login_required
from utils.query_safety import ERP_TABLES
from models.performance_log import PerformanceLog
from models.optimisation_recommendation import OptimisationRecommendation

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/dashboard')
@dashboard_bp.route('/api/dashboard/stats')
@login_required
def stats():
    try:
        with db.engine.connect() as conn:
            version = conn.exec_driver_sql('SELECT version()').scalar()
            counts = {t: conn.exec_driver_sql('SELECT COUNT(*) FROM public.' + t).scalar() for t in ERP_TABLES}
            indexes = conn.exec_driver_sql("SELECT count(*) FROM pg_indexes WHERE schemaname='public'").scalar()
            tables = conn.exec_driver_sql("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'").scalar()
        recent = [l.to_dict() for l in PerformanceLog.query.order_by(PerformanceLog.created_at.desc()).limit(20)]
        recommendations = OptimisationRecommendation.query.all()
        states = {state: sum(r.status == state for r in recommendations) for state in ('Pending', 'Applied', 'Rejected', 'Unsuccessful')}
        slow = PerformanceLog.query.filter(PerformanceLog.execution_time_before >= current_app.config['SLOW_QUERY_MS']).count()
        data = {'db_connected': True, 'postgresql_version': version, 'total_erp_records': sum(counts.values()), 'total_tables': tables,
                'total_indexes': indexes, 'row_counts': counts, 'slow_queries': slow, 'recommendations': states, 'recent_logs': recent,
                'last_measurement': recent[0]['created_at'] if recent else None, 'refreshed_at': datetime.now(timezone.utc).isoformat(),
                'status': 'Ready' if sum(counts.values()) else 'Dataset empty'}
        return jsonify(success=True, stats=data, data=data)
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(success=False, stats={'db_connected': False}, error='PostgreSQL unavailable or schema missing. Check .env and run setup.ps1.'), 503

@dashboard_bp.route('/api/database/status')
@login_required
def database_status():
    try:
        with db.engine.connect() as conn:
            version = conn.exec_driver_sql('SELECT version()').scalar()
        return jsonify(success=True, connected=True, version=version)
    except SQLAlchemyError:
        return jsonify(success=False, connected=False, error='PostgreSQL unavailable.'), 503
