from utils.time import utc_now
from models.user import db
from datetime import datetime

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    shipping_city = db.Column(db.String(100))
    order_date = db.Column(db.DateTime, default=utc_now)
    total_amount = db.Column(db.Numeric(14, 2), nullable=False)
    status = db.Column(db.String(30), default='Pending', nullable=False)
    
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete")
