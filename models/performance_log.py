from models.user import db
from datetime import datetime

class PerformanceLog(db.Model):
    __tablename__ = 'query_performance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.Text, nullable=False)
    execution_time_before = db.Column(db.Numeric(10, 6))
    execution_time_after = db.Column(db.Numeric(10, 6))
    optimization_applied = db.Column(db.Text)
    improvement_percentage = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
