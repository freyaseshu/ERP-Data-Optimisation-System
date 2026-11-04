"""A durable, reviewable optimization workflow and its administrator decisions."""
from utils.db import db
from utils.time import utc_now


class OptimizationRun(db.Model):
    __tablename__ = 'optimization_runs'

    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    profile = db.Column(db.String(30), nullable=False)
    configuration = db.Column(db.JSON, nullable=False)
    assessment = db.Column(db.JSON, nullable=False)
    actions = db.Column(db.JSON, nullable=False)

    def to_dict(self):
        return {c.name: (value.isoformat() if hasattr(value, 'isoformat') else value)
                for c in self.__table__.columns for value in [getattr(self, c.name)]}
