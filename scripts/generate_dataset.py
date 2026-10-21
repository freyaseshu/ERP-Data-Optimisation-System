"""Deterministic, atomic synthetic ERP loader. Nonempty databases are preserved."""
import argparse
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faker import Faker
from sqlalchemy import text
from werkzeug.security import generate_password_hash
from app import create_app
from utils.db import db
from utils.query_safety import ERP_TABLES

SIZES = {
    'small': dict(zip(ERP_TABLES, (10, 60, 600, 60, 300, 2000, 4500, 600, 1800, 1800))),
    'medium': dict(zip(ERP_TABLES, (20, 250, 4500, 250, 1200, 14000, 30000, 3000, 12000, 12000))),
    'large': dict(zip(ERP_TABLES, (35, 600, 9000, 500, 2500, 25000, 55000, 6000, 22000, 22000))),
}
CITIES = ['Chicago', 'New York', 'San Diego', 'San Francisco', 'Seattle', 'Austin', 'Denver', 'Boston', 'Houston', 'Phoenix']
CATEGORIES = ['Industrial Electronics', 'Heavy Machinery', 'Raw Materials', 'Safety & PPE', 'Office Automation']
STATUSES = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']

def money(value):
    return Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)

def generate_dataset(size='medium', scale=1, seed=42):
    if size not in SIZES or type(scale) is not int or not 1 <= scale <= 100:
        raise ValueError('Choose small/medium/large and an integer scale from 1 to 100.')
    counts = {t: n * scale for t, n in SIZES[size].items()}
    rng = random.Random(seed)
    fake = Faker()
    fake.seed_instance(seed)
    # Fixed reference makes reruns independent of wall-clock date.
    reference = datetime(2026, 1, 1)
    with db.engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(620431)'))
        # Blocks concurrent writes during empty-state check and insertion.
        conn.exec_driver_sql('LOCK TABLE ' + ', '.join(ERP_TABLES) + ' IN EXCLUSIVE MODE')
        actual = {t: conn.exec_driver_sql('SELECT COUNT(*) FROM ' + t).scalar() for t in ERP_TABLES}
        if any(actual.values()):
            print('Existing ERP records preserved. Use a NEW database for another profile.')
            print(actual)
            return actual
        def insert(table, records):
            model = db.metadata.tables[table]
            for i in range(0, len(records), 2000):
                conn.execute(model.insert(), records[i:i + 2000])
        def ids(table):
            return [r[0] for r in conn.exec_driver_sql('SELECT id FROM ' + table + ' ORDER BY id')]
        insert('departments', [dict(name=f'Department {i+1}', code=f'DEP-{i+1}', budget=money(rng.uniform(100000, 2000000)), location=rng.choice(CITIES)) for i in range(counts['departments'])])
        departments = ids('departments')
        insert('employees', [dict(department_id=rng.choice(departments), first_name=fake.first_name(), last_name=fake.last_name(), email=f'employee{i+1}@example.invalid', role=rng.choice(['Engineer', 'Sales', 'Manager', 'Analyst']), salary=money(rng.uniform(40000, 140000)), hire_date=(reference - timedelta(days=rng.randrange(1800))).date()) for i in range(counts['employees'])])
        employees = ids('employees')
        insert('customers', [dict(name=fake.company()[:100], email=f'customer{i+1}@example.invalid', city=rng.choice(CITIES), customer_segment=rng.choice(['Enterprise', 'Small Business', 'Government'])) for i in range(counts['customers'])])
        customers = ids('customers')
        insert('suppliers', [dict(name=fake.company()[:100], contact_name=fake.name(), email=f'supplier{i+1}@example.invalid', phone='555-0100', city=rng.choice(CITIES), country='US', rating=money(rng.uniform(1, 5))) for i in range(counts['suppliers'])])
        suppliers = ids('suppliers')
        products_data = []
        for i in range(counts['products']):
            cost = money(rng.uniform(10, 900))
            products_data.append(dict(supplier_id=rng.choice(suppliers), name=f'Synthetic Product {i+1}', sku=f'SKU-{i+1:08}', category=rng.choice(CATEGORIES), unit_price=money(cost * Decimal('1.50')), cost_price=cost))
        insert('products', products_data)
        products = {r[0]: r[1] for r in conn.exec_driver_sql('SELECT id, unit_price FROM products ORDER BY id')}
        product_ids = list(products)
        insert('orders', [dict(customer_id=rng.choice(customers), employee_id=rng.choice(employees), order_date=reference - timedelta(days=rng.randrange(730), minutes=rng.randrange(1440)), total_amount=0, status=rng.choice(STATUSES), shipping_city=rng.choice(CITIES)) for i in range(counts['orders'])])
        orders = ids('orders')
        items = []
        for i in range(counts['order_items']):
            oid = orders[i] if i < len(orders) else rng.choice(orders)
            pid = rng.choice(product_ids)
            quantity = rng.randint(1, 15)
            discount = rng.choice([Decimal('0'), Decimal('.05'), Decimal('.10')])
            items.append(dict(order_id=oid, product_id=pid, quantity=quantity, unit_price=products[pid], discount=discount, line_total=money(quantity * products[pid] * (1 - discount))))
        insert('order_items', items)
        conn.exec_driver_sql('UPDATE orders o SET total_amount = t.total FROM (SELECT order_id, SUM(line_total) AS total FROM order_items GROUP BY order_id) t WHERE o.id=t.order_id')
        # Unique product/warehouse positions; no accidental duplicate stock balances.
        insert('inventory', [dict(product_id=product_ids[i % len(product_ids)], warehouse_location=f'Warehouse {i // len(product_ids) + 1}', quantity_on_hand=rng.randrange(1200), reorder_level=50, last_restocked_at=reference - timedelta(days=rng.randrange(60))) for i in range(counts['inventory'])])
        order_rows = list(conn.exec_driver_sql('SELECT id, order_date, total_amount, status FROM orders ORDER BY id'))
        rng.shuffle(order_rows)
        insert('payments', [dict(order_id=o[0], payment_date=o[1] + timedelta(days=2), amount=o[2], payment_method=rng.choice(['Wire Transfer', 'ACH', 'Corporate Visa']), payment_status='Refunded' if o[3] == 'Cancelled' else 'Completed', transaction_ref=f'SYN-P-{o[0]}') for o in order_rows[:counts['payments']]])
        payments = list(conn.exec_driver_sql('SELECT id, payment_date, amount FROM payments ORDER BY id'))
        insert('transactions', [dict(payment_id=payments[i % len(payments)][0], account_code='4010-REV', transaction_type='Credit', amount=payments[i % len(payments)][2], transaction_date=payments[i % len(payments)][1], status='Posted', description='Synthetic payment ledger entry') for i in range(counts['transactions'])])
        actual = {t: conn.exec_driver_sql('SELECT COUNT(*) FROM ' + t).scalar() for t in ERP_TABLES}
        if actual != counts:
            raise RuntimeError('Row count mismatch; whole generation rolled back.')
    with db.engine.begin() as conn:
        for table in ERP_TABLES:
            conn.exec_driver_sql('ANALYZE ' + table)
    print(actual)
    print('Total ERP records:', sum(actual.values()))
    return actual

def seed_user(username, password, role):
    from models.user import User
    if not password or len(password) < 10:
        raise ValueError('Use a password of at least 10 characters.')
    if not User.query.filter_by(username=username).first():
        db.session.add(User(username=username, email=username + '@example.invalid', role=role, password=generate_password_hash(password)))
        db.session.commit()
        print('Created', username, '(existing passwords are never overwritten).')

if __name__ == '__main__':
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', choices=SIZES, default='medium')
    parser.add_argument('--scale', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    with create_app().app_context():
        generate_dataset(args.size, args.scale, args.seed)
        password = os.getenv('ERP_ADMIN_PASSWORD')
        if password:
            seed_user('admin', password, 'Admin')
        else:
            print('Set ERP_ADMIN_PASSWORD and run scripts/create_user.py to create a login.')
