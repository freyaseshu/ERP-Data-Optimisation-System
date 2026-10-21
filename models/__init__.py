"""
Import every model here so that `db.create_all()` in app.py can discover
all tables through a single import of the models package.
"""
from .user import User
from .customer import Customer
from .product import Product
from .inventory import Inventory
from .order import Order
from .order_item import OrderItem
from .performance_log import PerformanceLog, QueryPerformanceLog
from .department import Department
from .employee import Employee
from .supplier import Supplier
from .payment import Payment
from .transaction import Transaction
from .limitation import SystemLimitation
from .optimisation_recommendation import OptimisationRecommendation
from .archive_log import ArchiveLog
from .order_archive import OrderArchive

__all__ = [
    "User", "Customer", "Product", "Inventory", "Order", "OrderItem",
    "QueryPerformanceLog", "ArchiveLog", "OrderArchive",
]

# PostgreSQL enforces these invariants for all writers, including scripts.
from sqlalchemy import CheckConstraint
from utils.db import db
_RULES = {
    'users': [('role_valid', "role IN ('Admin', 'Analyst')")],
    'products': [('product_prices_nonnegative', 'unit_price >= 0 AND cost_price >= 0')],
    'inventory': [('inventory_nonnegative', 'quantity_on_hand >= 0 AND reorder_level >= 0')],
    'orders': [('order_amount_nonnegative', 'total_amount >= 0'), ('order_status_valid', "status IN ('Pending','Processing','Shipped','Delivered','Cancelled')")],
    'order_items': [('item_amount_valid', 'quantity > 0 AND unit_price >= 0 AND discount >= 0 AND discount <= 1 AND line_total >= 0')],
    'payments': [('payment_nonnegative', 'amount >= 0')],
    'transactions': [('transaction_nonnegative', 'amount >= 0')],
    'optimisation_recommendations': [('recommendation_status_valid', "status IN ('Pending','Applied','Rejected','Unsuccessful')")],
}
for _table, _rules in _RULES.items():
    for _name, _expression in _rules:
        db.metadata.tables[_table].append_constraint(CheckConstraint(_expression, name=_name))
