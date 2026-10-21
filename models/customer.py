from utils.time import utc_now
from models.user import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100))
    customer_segment = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=utc_now)
    
    orders = db.relationship('Order', backref='customer', lazy=True, cascade="all, delete")
