from utils.db import db
from datetime import datetime

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    budget = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='department', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'budget': float(self.budget) if self.budget is not None else 0.0,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
