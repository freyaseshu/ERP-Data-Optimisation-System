from utils.time import utc_now
from models.user import db
from datetime import datetime

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity_on_hand = db.Column(db.Integer, nullable=False, default=0)
    quantity = db.synonym('quantity_on_hand')
    reorder_level = db.Column(db.Integer, nullable=False, default=50)
    last_restocked_at = db.Column(db.DateTime, default=utc_now)
    warehouse_location = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
