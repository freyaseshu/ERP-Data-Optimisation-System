from utils.time import utc_now
from utils.db import db
from datetime import datetime

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=utc_now)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(30), nullable=False, default='Completed')
    transaction_ref = db.Column(db.String(100), unique=True, nullable=False)

    transactions = db.relationship('Transaction', backref='payment', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_ref': self.transaction_ref
        }
