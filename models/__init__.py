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
from .performance_log import QueryPerformanceLog
from .archive_log import ArchiveLog
from .order_archive import OrderArchive

__all__ = [
    "User", "Customer", "Product", "Inventory", "Order", "OrderItem",
    "QueryPerformanceLog", "ArchiveLog", "OrderArchive",
]
