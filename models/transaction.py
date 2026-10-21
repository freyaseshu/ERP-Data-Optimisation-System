from utils.time import utc_now
from utils.db import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='SET NULL'))
    account_code = db.Column(db.String(30), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=utc_now)
    status = db.Column(db.String(30), nullable=False, default='Posted')
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'account_code': self.account_code,
            'transaction_type': self.transaction_type,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'status': self.status,
            'description': self.description
        }
