from utils.time import utc_now
from models.user import db
from datetime import datetime

class PerformanceLog(db.Model):
    __tablename__ = 'query_performance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.Text, nullable=False)
    query_name = db.Column(db.String(150))
    status = db.Column(db.String(30), nullable=False, default='Analysed')
    details = db.Column(db.JSON)
    execution_time_before = db.Column(db.Numeric(10, 6))
    execution_time_after = db.Column(db.Numeric(10, 6))
    optimization_applied = db.Column(db.Text)
    improvement_percentage = db.Column(db.Numeric(14, 2))
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {c.name: (float(v) if c.name in ('execution_time_before', 'execution_time_after', 'improvement_percentage') and v is not None else v.isoformat() if hasattr(v, 'isoformat') else v)
                for c in self.__table__.columns for v in [getattr(self, c.name)]}

QueryPerformanceLog = PerformanceLog
