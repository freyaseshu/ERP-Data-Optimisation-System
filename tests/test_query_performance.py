import os
import time
import csv
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Extract connection details from DATABASE_URL if available, else fall back to separate vars
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('mysql'):
    # e.g. mysql+pymysql://root:password@localhost/erp_db
    import re
    match = re.search(r'://([^:]+):([^@]+)@([^/]+)/(.+)', database_url)
    if match:
        DB_USER = match.group(1)
        DB_PASSWORD = match.group(2)
        DB_HOST = match.group(3)
        DB_NAME = match.group(4)
    else:
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_USER = os.getenv('DB_USER', 'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_NAME = os.getenv('DB_NAME', 'erp_optimisation_db')
else:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'erp_optimisation_db')

QUERIES = [
    {
        "name": "Query 1: Retrieve customers in a specific city",
        "sql": "SELECT * FROM customers WHERE city = 'New York';"
    },
    {
        "name": "Query 2: Join customers and orders",
        "sql": "SELECT c.name, o.order_date, o.total_amount FROM customers c JOIN orders o ON c.id = o.customer_id;"
    },
    {
        "name": "Query 3: Search products by category",
        "sql": "SELECT * FROM products WHERE category = 'Electronics';"
    },
    {
        "name": "Query 4: Join orders and order_items and calculate totals",
        "sql": "SELECT o.id, SUM(oi.price * oi.quantity) as calc_total FROM orders o JOIN order_items oi ON o.id = oi.order_id GROUP BY o.id;"
    }
]

def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return conn
    except pymysql.Error as err:
        print(f"Error: {err}")
        print("Please check your database connection details in the .env file and ensure the database exists.")
        return None

def run_performance_tests(output_filename="results_before.csv", apply_optimizations=False):
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    if apply_optimizations:
        print("Applying basic optimizations (creating indexes)...")
        try:
            cursor.execute("CREATE INDEX idx_customers_city ON customers(city);")
            cursor.execute("CREATE INDEX idx_orders_customer_id ON orders(customer_id);")
            cursor.execute("CREATE INDEX idx_products_category ON products(category);")
            conn.commit()
            print("Optimizations applied successfully.")
        except pymysql.Error as err:
            # Indexes might already exist
            print(f"Index creation note: {err}")
    
    results = []
    
    for q in QUERIES:
        query_name = q["name"]
        sql = q["sql"]
        
        # Measure Execution Time
        start_time = time.time()
        cursor.execute(sql)
        rows = cursor.fetchall()
        execution_time_ms = (time.time() - start_time) * 1000
        rows_returned = len(rows)
        
        # Run EXPLAIN
        cursor.execute(f"EXPLAIN {sql}")
        explain_plan = cursor.fetchone()
        
        results.append({
            "query_name": query_name,
            "execution_time_ms": round(execution_time_ms, 2),
            "rows_returned": rows_returned,
            "key_used": explain_plan.get("key", "None"),
            "rows_examined": explain_plan.get("rows", 0),
            "notes": "After optimisation" if apply_optimizations else "Before optimisation"
        })
        
    cursor.close()
    conn.close()
    
    # Save to CSV
    output_path = os.path.join(os.path.dirname(__file__), output_filename)
    with open(output_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["query_name", "execution_time_ms", "rows_returned", "key_used", "rows_examined", "notes"])
        writer.writeheader()
        writer.writerows(results)
        
    print(f"Saved results to {output_path}")

if __name__ == "__main__":
    print("--- PHASE 4: BEFORE OPTIMIZATION ---")
    run_performance_tests("results_before.csv", apply_optimizations=False)
    
    print("\n--- PHASE 5 & 6: APPLY OPTIMIZATION & AFTER OPTIMIZATION ---")
    run_performance_tests("results_after.csv", apply_optimizations=True)
    
    print("\nTests completed successfully.")
