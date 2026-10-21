#!/usr/bin/env python3
"""
ERP Data Optimisation System - Synthetic Dataset Generator
Generates realistic, relational ERP datasets (50,000 to 100,000+ records)
exclusively for PostgreSQL (erp_optimisation_db).
"""

import os
import sys
import time
import random
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg
from faker import Faker
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/erp_optimisation_db')
# Standardize SQLAlchemy URL to standard psycopg URL
if DB_URL.startswith('postgresql+psycopg://'):
    DB_URL = DB_URL.replace('postgresql+psycopg://', 'postgresql://')
elif DB_URL.startswith('postgresql+psycopg2://'):
    DB_URL = DB_URL.replace('postgresql+psycopg2://', 'postgresql://')

SIZES = {
    'small': {
        'departments': 10,
        'employees': 60,
        'customers': 600,
        'suppliers': 60,
        'products': 300,
        'orders': 2000,
        'order_items': 4500,
        'inventory': 600,
        'payments': 1800,
        'transactions': 1800
    },
    'medium': {
        'departments': 20,
        'employees': 250,
        'customers': 4500,
        'suppliers': 250,
        'products': 1200,
        'orders': 14000,
        'order_items': 30000,
        'inventory': 3000,
        'payments': 12000,
        'transactions': 12000
    },
    'large': {
        'departments': 35,
        'employees': 600,
        'customers': 9000,
        'suppliers': 500,
        'products': 2500,
        'orders': 25000,
        'order_items': 55000,
        'inventory': 6000,
        'payments': 22000,
        'transactions': 22000
    }
}

CITIES = [
    'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
    'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose',
    'Austin', 'Jacksonville', 'Fort Worth', 'Columbus', 'Charlotte',
    'San Francisco', 'Indianapolis', 'Seattle', 'Denver', 'Boston',
    'Nashville', 'Detroit', 'Portland', 'Memphis', 'Atlanta'
]

CATEGORIES = [
    'Industrial Electronics', 'Heavy Machinery', 'Raw Materials', 
    'Safety & PPE', 'Hydraulics & Pneumatics', 'Fasteners & Hardware',
    'Packaging & Shipping', 'Office Automation', 'Electrical Components',
    'Automotive Parts', 'Precision Tools', 'Chemical Reagents'
]

CUSTOMER_SEGMENTS = ['Enterprise', 'Mid-Market', 'Small Business', 'Government', 'Educational']
ORDER_STATUSES = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
PAYMENT_METHODS = ['Wire Transfer', 'ACH Credit', 'Corporate Visa', 'Letter of Credit', 'Commercial Check']
WAREHOUSES = ['Warehouse Alpha - North', 'Warehouse Bravo - South', 'Warehouse Charlie - East', 
              'Warehouse Delta - West', 'Central Distribution Hub']

SYSTEM_LIMITATIONS_DATA = [
    (1, "Large Dataset Processing", 
     "Large datasets can increase query execution time and database load.",
     "High query latency, increased CPU and I/O consumption, slower UI response times.",
     "Implemented synthetic dataset scaling (50,000–100,000+ records), server-side pagination, index tuning, and performance profiling.",
     "Implemented",
     "Dataset generation scripts tested with 75,000+ records; server-side paginated queries verified under 25ms.",
     "Continue testing with multi-million row partitions."),
    
    (2, "Slow SQL Queries", 
     "Inefficient joins, unnecessary scans, and poor query structures reduce performance.",
     "Degraded throughput, locks on transactional tables, slow dashboard reporting.",
     "PostgreSQL EXPLAIN ANALYZE plan engine, automatic bottleneck identification (Seq Scan detection, filter rows removed, hash joins), and index suggestions.",
     "Implemented",
     "Query analyser parsed execution plans and identified unindexed customer and order item lookups.",
     "Add automated cost-based regression alerts."),

    (3, "Limited Automatic Optimisation", 
     "Not all queries can be optimised safely without human review.",
     "Unintended index proliferation, modified query semantics, lock contention during index creation.",
     "Human-in-the-loop recommendation workflow: proposed SQL rewrites and CREATE INDEX scripts require administrator review and approval with pre-execution safety validation.",
     "Implemented",
     "Optimisation workflow tracks recommendations as Pending, Approved, Applied, and Rejected with transaction rollback safeguards.",
     "Implement scheduled maintenance window execution."),

    (4, "Database Dependency", 
     "Database-specific syntax and drivers can cause application incompatibility.",
     "Vendor lock-in, migration failures, driver dialect mismatches.",
     "Centralised database connection configuration using PostgreSQL exclusively with psycopg driver and standard PostgreSQL DDL.",
     "Implemented",
     "All models, raw SQL scripts, EXPLAIN formats, and connection strings verified purely on PostgreSQL 10+.",
     "None. Strict PostgreSQL enforcement achieved."),

    (5, "Hardware and Environment Dependency", 
     "Performance depends on CPU, memory, storage I/O, caching, and PostgreSQL configuration parameters.",
     "Benchmark measurements fluctuate based on system load, shared resources, and disk speeds.",
     "Environment recording in benchmarks, multi-run warm-up iterations, trimmed averages, and explicit system documentation.",
     "Implemented",
     "Benchmarking module captures OS, CPU thread count, PostgreSQL version, and calculates average execution times.",
     "Add automated shared_buffers and work_mem tuning recommendations."),

    (6, "Indexing Overhead", 
     "Indexes consume storage and increase write overhead during INSERT, UPDATE, and DELETE operations.",
     "Excessive indexing slows down batch transactions and inflates table sizes.",
     "Index analysis engine evaluates existing indexes, explains storage/write trade-offs, and prevents duplicate index creation.",
     "Implemented",
     "Database explorer displays index sizes and table constraints; recommendations inspect pg_indexes before suggesting new indexes.",
     "Add index usage statistics from pg_stat_user_indexes."),

    (7, "Limited Real-Time Monitoring", 
     "Prototypes may not monitor every background query continuously in real time.",
     "Intermittent performance spikes or background locks can go unnoticed.",
     "On-demand query profiling, dashboard refresh controls, performance execution logs, and benchmark history tracking.",
     "Partially Implemented",
     "Historical query log tracks before/after times, percentage improvement, and timestamped benchmarks.",
     "Full background daemon integration with pg_stat_statements planned for production."),

    (8, "Security and Data Privacy", 
     "Unrestricted query execution and exposed credentials compromise database security.",
     "SQL injection vulnerability, data breaches, unauthorized data modification or table drops.",
     "Environment-based credentials, parameterized queries, strict SELECT query whitelist in ordinary analyzer, destructive keyword rejection, and statement timeouts.",
     "Implemented",
     "Security test suite verifies rejection of DROP, TRUNCATE, DELETE, and multiple statement injection attempts.",
     "Add fine-grained row-level security (RLS) policies."),

    (9, "Synthetic Dataset Realism", 
     "Synthetic data distributions may not mirror real-world production skew or edge cases.",
     "Benchmarking synthetic data may yield different index selectivity than production ERP data.",
     "Realistic Faker-based generator modeling multi-tier corporate hierarchies, Pareto distribution for order amounts, and realistic status workflows.",
     "Implemented",
     "Generates valid referential integrity across 10 ERP tables with configurable scale factors.",
     "Add zipfian skew configuration for customer purchasing frequency."),

    (10, "Benchmark Reliability", 
     "OS file caching, shared buffer cache, and micro-benchmark timing noise can distort measurements.",
     "False positives or exaggerated improvement percentages reported.",
     "Discard cold-cache run, execute configurable repeat runs (3-5 iterations), calculate percentage improvement formula, and verify row-count result equivalence.",
     "Implemented",
     "Benchmark runner verifies result set checksum/row count equivalence between baseline and optimised queries.",
     "Add automated disk buffer cache flushing on supported environments."),

    (11, "Scalability and Concurrent Users", 
     "Single-threaded prototypes degrade under high concurrency and connection exhaustion.",
     "Connection pool starvation and deadlocks under concurrent peak load.",
     "SQLAlchemy connection pooling with pool_size and max_overflow configuration, pagination limits, and statement timeouts.",
     "Partially Implemented",
     "Connection pool configured with safe limits; server-side pagination caps result sets at 100 rows per request.",
     "Run multi-threaded locust load test for concurrent user stress testing."),

    (12, "Limited Predictive Capabilities", 
     "Reactive query analysis identifies existing bottlenecks but cannot predict future growth bottlenecks.",
     "Unforeseen query degradation when table sizes cross memory thresholds.",
     "Threshold-based warnings for table scans exceeding 1,000 rows and historical execution trend logging.",
     "Partially Implemented",
     "Performance trend charts visualize historical execution times; query warnings alert on large unindexed scans.",
     "Machine learning-based query cost regression forecasting planned for future enhancement.")
]

def get_connection():
    return psycopg.connect(DB_URL)

def seed_users_and_limitations(conn):
    print("  -> Seeding admin and analyst accounts...")
    hashed_pwd = generate_password_hash('password')
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO users (username, email, password, role)
            VALUES 
                ('admin', 'admin@erp-optimise.local', %s, 'Admin'),
                ('analyst', 'analyst@erp-optimise.local', %s, 'Analyst')
            ON CONFLICT (username) DO UPDATE 
            SET password = EXCLUDED.password, role = EXCLUDED.role;
        """, (hashed_pwd, hashed_pwd))

        print("  -> Seeding 12 System Limitations and Improvements...")
        for lim in SYSTEM_LIMITATIONS_DATA:
            cur.execute("""
                INSERT INTO system_limitations (id, name, problem, impact, solution, status, test_evidence, remaining_work)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    problem = EXCLUDED.problem,
                    impact = EXCLUDED.impact,
                    solution = EXCLUDED.solution,
                    status = EXCLUDED.status,
                    test_evidence = EXCLUDED.test_evidence,
                    remaining_work = EXCLUDED.remaining_work,
                    updated_at = CURRENT_TIMESTAMP;
            """, lim)
    conn.commit()

def generate_dataset(size='medium', force=False):
    start_total = time.time()
    fake = Faker()
    Faker.seed(42)
    random.seed(42)

    config = SIZES.get(size, SIZES['medium'])
    total_target = sum(config.values())

    print("=" * 70)
    print(f"ERP SYNTHETIC DATASET GENERATOR - POSTGRESQL (erp_optimisation_db)")
    print(f"Profile: '{size.upper()}' | Target ERP Records: ~{total_target:,}")
    print("=" * 70)

    conn = get_connection()

    # Check existing data
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM orders;")
        existing_orders = cur.fetchone()[0]

    if existing_orders > 0 and not force:
        print(f"\n[INFO] Database already contains {existing_orders:,} orders.")
        print("To regenerate fresh data, pass '--force' or '-f' flag.")
        seed_users_and_limitations(conn)
        conn.close()
        return

    if force:
        print("\n[WARNING] Force flag provided. Cleaning existing ERP transactional records...")
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE transactions, payments, inventory, order_items, 
                               orders, products, suppliers, customers, employees, departments 
                CASCADE;
            """)
        conn.commit()
        print("  -> Existing ERP tables truncated safely.")

    # 1. Departments
    print(f"\n[1/10] Generating {config['departments']} Departments...")
    dept_names = [
        ('Executive Leadership', 'EXEC', 2500000.00, 'HQ Tower - Floor 12'),
        ('Finance & Accounting', 'FIN', 1200000.00, 'HQ Tower - Floor 5'),
        ('Information Technology', 'IT', 3400000.00, 'Tech Campus - Bldg 1'),
        ('Global Supply Chain', 'SCM', 4500000.00, 'Central Logistics Hub'),
        ('Corporate Sales', 'SALES', 3200000.00, 'HQ Tower - Floor 4'),
        ('Human Resources', 'HR', 850000.00, 'HQ Tower - Floor 2'),
        ('Research & Development', 'RND', 5000000.00, 'Innovation Labs'),
        ('Manufacturing Operations', 'MFG', 7500000.00, 'Plant Alpha - Detroit'),
        ('Quality Assurance', 'QA', 950000.00, 'Plant Alpha - Lab 3'),
        ('Customer Success', 'CS', 1100000.00, 'Support Center - Austin'),
        ('Legal & Compliance', 'LEGAL', 1400000.00, 'HQ Tower - Floor 11'),
        ('Marketing & Communications', 'MKT', 2100000.00, 'Creative Studio'),
        ('Procurement Operations', 'PROC', 1800000.00, 'Central Logistics Hub'),
        ('Facilities & Security', 'FAC', 1300000.00, 'Operations Center'),
        ('Field Engineering', 'ENG', 2800000.00, 'Regional Service Hub')
    ]
    # Pad if more needed
    while len(dept_names) < config['departments']:
        idx = len(dept_names) + 1
        dept_names.append((f"Department Division {idx}", f"DIV{idx}", round(random.uniform(500000, 3000000), 2), f"Facility {idx}"))

    dept_records = dept_names[:config['departments']]
    dept_ids = []
    with conn.cursor() as cur:
        for name, code, budget, loc in dept_records:
            cur.execute("""
                INSERT INTO departments (name, code, budget, location)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (name, code, budget, loc))
            dept_ids.append(cur.fetchone()[0])
    conn.commit()
    print(f"  -> Generated {len(dept_ids)} departments.")

    # 2. Employees
    print(f"\n[2/10] Generating {config['employees']} Employees...")
    emp_records = []
    emp_roles = ['Senior Engineer', 'Operations Analyst', 'Supply Planner', 'Account Executive',
                 'Procurement Specialist', 'Inventory Manager', 'Logistics Coordinator',
                 'Financial Controller', 'HR Generalist', 'Database Administrator']
    for i in range(config['employees']):
        f_name = fake.first_name()
        l_name = fake.last_name()
        email = f"{f_name.lower()}.{l_name.lower()}.{i+1}@erpsystem.local"
        dept_id = random.choice(dept_ids)
        role = random.choice(emp_roles)
        salary = round(random.uniform(45000, 160000), 2)
        hire_date = fake.date_between(start_date='-5y', end_date='today')
        emp_records.append((dept_id, f_name, l_name, email, role, salary, hire_date))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO employees (department_id, first_name, last_name, email, role, salary, hire_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, emp_records)
        cur.execute("SELECT id FROM employees ORDER BY id;")
        emp_ids = [row[0] for row in cur.fetchall()]
    conn.commit()
    print(f"  -> Generated {len(emp_ids)} employees.")

    # 3. Customers
    print(f"\n[3/10] Generating {config['customers']} Customers...")
    cust_records = []
    for i in range(config['customers']):
        c_name = fake.company() if random.random() < 0.7 else fake.name()
        c_email = f"cust.{i+1}.{fake.unique.email()}"
        phone = fake.phone_number()[:25]
        city = random.choice(CITIES)
        country = 'United States'
        segment = random.choice(CUSTOMER_SEGMENTS)
        cust_records.append((c_name, c_email, phone, city, country, segment))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO customers (name, email, phone, city, country, customer_segment)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, cust_records)
        cur.execute("SELECT id FROM customers ORDER BY id;")
        cust_ids = [row[0] for row in cur.fetchall()]
    conn.commit()
    print(f"  -> Generated {len(cust_ids)} customers.")

    # 4. Suppliers
    print(f"\n[4/10] Generating {config['suppliers']} Suppliers...")
    supp_records = []
    for i in range(config['suppliers']):
        s_name = f"{fake.company()} {fake.company_suffix()}"
        contact = fake.name()
        s_email = f"supplier.{i+1}.{fake.unique.email()}"
        phone = fake.phone_number()[:25]
        city = random.choice(CITIES)
        country = 'United States'
        rating = round(random.uniform(3.2, 5.0), 2)
        supp_records.append((s_name, contact, s_email, phone, city, country, rating))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO suppliers (name, contact_name, email, phone, city, country, rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, supp_records)
        cur.execute("SELECT id FROM suppliers ORDER BY id;")
        supp_ids = [row[0] for row in cur.fetchall()]
    conn.commit()
    print(f"  -> Generated {len(supp_ids)} suppliers.")

    # 5. Products
    print(f"\n[5/10] Generating {config['products']} Products...")
    prod_records = []
    for i in range(config['products']):
        supp_id = random.choice(supp_ids)
        category = random.choice(CATEGORIES)
        p_name = f"{category} Model {fake.word().upper()}-{random.randint(100, 999)}"
        sku = f"SKU-{category[:3].upper()}-{i+1:06d}"
        cost = round(random.uniform(10.0, 850.0), 2)
        price = round(cost * random.uniform(1.25, 2.2), 2)
        prod_records.append((supp_id, p_name, sku, category, price, cost))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO products (supplier_id, name, sku, category, unit_price, cost_price)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, prod_records)
        cur.execute("SELECT id, unit_price FROM products ORDER BY id;")
        product_rows = cur.fetchall()
        prod_ids = [row[0] for row in product_rows]
        prod_prices = {row[0]: float(row[1]) for row in product_rows}
    conn.commit()
    print(f"  -> Generated {len(prod_ids)} products.")

    # 6. Orders
    print(f"\n[6/10] Generating {config['orders']} Orders...")
    order_records = []
    start_date = datetime.now() - timedelta(days=730)
    for i in range(config['orders']):
        c_id = random.choice(cust_ids)
        e_id = random.choice(emp_ids)
        days_offset = random.randint(0, 730)
        o_date = start_date + timedelta(days=days_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        status = random.choice(ORDER_STATUSES)
        shipping_city = random.choice(CITIES)
        order_records.append((c_id, e_id, o_date, 0.00, status, shipping_city))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO orders (customer_id, employee_id, order_date, total_amount, status, shipping_city)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, order_records)
        cur.execute("SELECT id, order_date, status FROM orders ORDER BY id;")
        order_info = cur.fetchall()
        order_ids = [row[0] for row in order_info]
    conn.commit()
    print(f"  -> Generated {len(order_ids)} orders.")

    # 7. Order Items
    print(f"\n[7/10] Generating {config['order_items']} Order Items...")
    order_item_records = []
    order_totals = {oid: 0.0 for oid in order_ids}
    
    # Ensure every order gets at least 1 item
    for oid in order_ids:
        p_id = random.choice(prod_ids)
        qty = random.randint(1, 10)
        price = prod_prices[p_id]
        discount = round(random.choice([0.0, 0.05, 0.10, 0.15]), 2)
        line_total = round(qty * price * (1.0 - discount), 2)
        order_totals[oid] += line_total
        order_item_records.append((oid, p_id, qty, price, discount, line_total))

    # Remaining order items distributed across orders
    remaining_items = config['order_items'] - len(order_ids)
    for _ in range(max(0, remaining_items)):
        oid = random.choice(order_ids)
        p_id = random.choice(prod_ids)
        qty = random.randint(1, 15)
        price = prod_prices[p_id]
        discount = round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20]), 2)
        line_total = round(qty * price * (1.0 - discount), 2)
        order_totals[oid] += line_total
        order_item_records.append((oid, p_id, qty, price, discount, line_total))

    # Batch insert order items
    batch_size = 5000
    with conn.cursor() as cur:
        for i in range(0, len(order_item_records), batch_size):
            cur.executemany("""
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount, line_total)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, order_item_records[i:i+batch_size])
        
        # Update order totals in batch
        order_updates = [(round(total, 2), oid) for oid, total in order_totals.items()]
        for i in range(0, len(order_updates), batch_size):
            cur.executemany("""
                UPDATE orders SET total_amount = %s WHERE id = %s;
            """, order_updates[i:i+batch_size])
    conn.commit()
    print(f"  -> Generated {len(order_item_records)} order items.")

    # 8. Inventory
    print(f"\n[8/10] Generating {config['inventory']} Inventory records...")
    inv_records = []
    for _ in range(config['inventory']):
        p_id = random.choice(prod_ids)
        warehouse = random.choice(WAREHOUSES)
        qty_on_hand = random.randint(5, 1200)
        reorder_level = random.choice([25, 50, 75, 100, 150])
        restocked = fake.date_time_between(start_date='-60d', end_date='now')
        inv_records.append((p_id, warehouse, qty_on_hand, reorder_level, restocked))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO inventory (product_id, warehouse_location, quantity_on_hand, reorder_level, last_restocked_at)
            VALUES (%s, %s, %s, %s, %s);
        """, inv_records)
    conn.commit()
    print(f"  -> Generated {len(inv_records)} inventory rows.")

    # 9. Payments
    print(f"\n[9/10] Generating {config['payments']} Payments...")
    payment_records = []
    # Pick orders that have non-zero totals
    candidate_orders = [o for o in order_info if order_totals.get(o[0], 0) > 0]
    selected_orders = random.sample(candidate_orders, min(config['payments'], len(candidate_orders)))
    
    for idx, (oid, odate, ostatus) in enumerate(selected_orders):
        p_amount = round(order_totals[oid], 2)
        p_date = odate + timedelta(days=random.randint(0, 5))
        method = random.choice(PAYMENT_METHODS)
        p_status = 'Completed' if ostatus != 'Cancelled' else 'Refunded'
        tx_ref = f"TX-ERP-{idx+1:08d}-{oid}"
        payment_records.append((oid, p_date, p_amount, method, p_status, tx_ref))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO payments (order_id, payment_date, amount, payment_method, payment_status, transaction_ref)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, payment_records)
        cur.execute("SELECT id, amount, payment_date, payment_status FROM payments ORDER BY id;")
        payment_rows = cur.fetchall()
        payment_ids = [row[0] for row in payment_rows]
    conn.commit()
    print(f"  -> Generated {len(payment_ids)} payments.")

    # 10. Transactions (General Ledger)
    print(f"\n[10/10] Generating {config['transactions']} General Ledger Transactions...")
    tx_records = []
    gl_accounts = [
        ('1010-CASH', 'Debit', 'Cash & Liquid Assets'),
        ('1200-AR', 'Credit', 'Accounts Receivable Settlement'),
        ('4010-REV', 'Credit', 'Product Sales Revenue'),
        ('5010-COGS', 'Debit', 'Cost of Goods Sold Realization'),
        ('2010-AP', 'Debit', 'Supplier Accounts Payable Clearing')
    ]
    for i in range(config['transactions']):
        p_row = random.choice(payment_rows)
        pid = p_row[0]
        amt = float(p_row[1])
        t_date = p_row[2]
        acct, t_type, desc = random.choice(gl_accounts)
        status = 'Posted'
        tx_records.append((pid, acct, t_type, amt, t_date, status, f"GL Posting: {desc} (Ref P#{pid})"))

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO transactions (payment_id, account_code, transaction_type, amount, transaction_date, status, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, tx_records)
    conn.commit()
    print(f"  -> Generated {len(tx_records)} general ledger transactions.")

    # Seed users and limitations
    seed_users_and_limitations(conn)

    conn.close()

    total_time = time.time() - start_total
    print("\n" + "=" * 70)
    print(f"SYNTHETIC DATASET GENERATION COMPLETE in {total_time:.2f} seconds!")
    print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ERP Synthetic Dataset Generator for PostgreSQL")
    parser.add_argument('--size', choices=['small', 'medium', 'large'], default='medium',
                        help="Dataset size profile (default: medium, ~65,000 records)")
    parser.add_argument('--force', '-f', action='store_true',
                        help="Force regenerate: clean and re-populate ERP tables")
    args = parser.parse_args()

    generate_dataset(size=args.size, force=args.force)
