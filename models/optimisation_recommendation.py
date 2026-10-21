from utils.db import db
from datetime import datetime

class OptimisationRecommendation(db.Model):
    __tablename__ = 'optimisation_recommendations'

    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.Text, nullable=False)
    recommendation_type = db.Column(db.String(30), nullable=False)  # 'INDEX', 'REWRITE', 'JOIN'
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sql_statement = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='Pending')  # 'Pending', 'Applied', 'Rejected', 'Unsuccessful'
    applied_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'query_text': self.query_text,
            'recommendation_type': self.recommendation_type,
            'title': self.title,
            'description': self.description,
            'sql_statement': self.sql_statement,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
