from utils.time import utc_now
from utils.db import db
from datetime import datetime

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    city = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Numeric(3, 2), default=4.00)
    created_at = db.Column(db.DateTime, default=utc_now)

    products = db.relationship('Product', backref='supplier', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_name': self.contact_name,
            'email': self.email,
            'phone': self.phone,
            'city': self.city,
            'country': self.country,
            'rating': float(self.rating) if self.rating is not None else 4.0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
