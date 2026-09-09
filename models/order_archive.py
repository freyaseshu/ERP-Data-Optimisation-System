"""
Mirror of the `orders` table used as the archive destination for the
Data Archive module (orders -> orders_archive).
"""
from datetime import datetime
from utils.db import db


class OrderArchive(db.Model):
    __tablename__ = 'orders_archive'

    id = db.Column(db.Integer, primary_key=True)
    original_order_id = db.Column(db.Integer, nullable=False, index=True)
    customer_id = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime)
    total_amount = db.Column(db.Numeric(12, 2))
    status = db.Column(db.String(50))
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "original_order_id": self.original_order_id,
            "customer_id": self.customer_id,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "total_amount": float(self.total_amount) if self.total_amount is not None else None,
            "status": self.status,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }
