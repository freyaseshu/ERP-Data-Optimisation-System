from utils.db import db
from datetime import datetime

class SystemLimitation(db.Model):
    __tablename__ = 'system_limitations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    problem = db.Column(db.Text, nullable=False)
    impact = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default='Implemented')  # Implemented, Partially Implemented, Planned, Blocked
    test_evidence = db.Column(db.Text)
    remaining_work = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'problem': self.problem,
            'impact': self.impact,
            'solution': self.solution,
            'status': self.status,
            'test_evidence': self.test_evidence,
            'remaining_work': self.remaining_work,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
