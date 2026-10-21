from utils.time import utc_now
from models.user import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    price = db.synonym('unit_price')
    cost_price = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    inventory = db.relationship('Inventory', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True, cascade="all, delete")
