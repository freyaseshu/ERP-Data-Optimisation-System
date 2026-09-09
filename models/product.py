from models.user import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    inventory = db.relationship('Inventory', backref='product', uselist=False, cascade="all, delete")
    order_items = db.relationship('OrderItem', backref='product', lazy=True, cascade="all, delete")
