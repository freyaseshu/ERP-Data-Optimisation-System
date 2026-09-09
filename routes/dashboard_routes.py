from flask import Blueprint, render_template, session, redirect, url_for

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    from models.customer import Customer
    from models.product import Product
    from models.order import Order
    from models.inventory import Inventory
    from models.archive_log import ArchiveLog
    from models.performance_log import PerformanceLog
    
    total_customers = Customer.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_inventory = Inventory.query.count()
    
    # We will need some dummy data for charts if none exists
    
    return render_template('dashboard.html', 
                           total_customers=total_customers,
                           total_products=total_products,
                           total_orders=total_orders,
                           total_inventory=total_inventory)
