import random
from datetime import datetime, timedelta

def generate_sql():
    sql = "USE erp_db;\n\n"

    # Insert Users
    sql += "INSERT INTO users (username, email, password, role) VALUES\n"
    sql += "('admin', 'admin@erp.com', 'scrypt:32768:8:1$C6Z2X7xY...$b1', 'Admin'),\n" # We'll need a real hash later, this is dummy for now
    sql += "('analyst', 'analyst@erp.com', 'scrypt:32768:8:1$C6Z2X7xY...$b2', 'Analyst');\n\n"

    # Insert Customers (500)
    cities = ['New York', 'London', 'Tokyo', 'Paris', 'Berlin', 'Sydney', 'Toronto', 'Dubai']
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'company.com']
    
    sql += "INSERT INTO customers (name, email, city) VALUES\n"
    customer_values = []
    for i in range(1, 501):
        name = f"Customer {i}"
        email = f"customer{i}@{random.choice(domains)}"
        city = random.choice(cities)
        customer_values.append(f"('{name}', '{email}', '{city}')")
    
    # Add intentional duplicates
    for i in range(1, 11):
        name = f"Duplicate Customer {i}"
        email = f"dup{i}@{domains[0]}"
        city = cities[0]
        customer_values.append(f"('{name}', '{email}', '{city}')")
        customer_values.append(f"('{name}', '{email}', '{city}')") # Duplicate email and name
        
    sql += ",\n".join(customer_values) + ";\n\n"

    # Insert Products (200)
    categories = ['Electronics', 'Furniture', 'Clothing', 'Software', 'Hardware']
    sql += "INSERT INTO products (name, category, price) VALUES\n"
    product_values = []
    for i in range(1, 201):
        name = f"Product {i}"
        cat = random.choice(categories)
        price = round(random.uniform(10.0, 1000.0), 2)
        product_values.append(f"('{name}', '{cat}', {price})")
        
    # Intentional duplicate products
    for i in range(1, 6):
        name = f"Duplicate Product {i}"
        cat = categories[0]
        price = 99.99
        product_values.append(f"('{name}', '{cat}', {price})")
        product_values.append(f"('{name}', '{cat}', {price})") # Duplicate name, cat, price
        
    sql += ",\n".join(product_values) + ";\n\n"

    # Insert Inventory (for the 210 products)
    sql += "INSERT INTO inventory (product_id, quantity, warehouse_location) VALUES\n"
    inventory_values = []
    for i in range(1, 211):
        qty = random.randint(0, 500)
        loc = f"Warehouse {random.choice(['A', 'B', 'C'])}"
        inventory_values.append(f"({i}, {qty}, '{loc}')")
    sql += ",\n".join(inventory_values) + ";\n\n"

    # Insert Orders (5000)
    sql += "INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES\n"
    order_values = []
    statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    
    start_date = datetime.now() - timedelta(days=365*3) # 3 years ago
    
    for i in range(1, 5001):
        cust_id = random.randint(1, 510)
        days_offset = random.randint(0, 365*3)
        order_date = start_date + timedelta(days=days_offset)
        status = random.choice(statuses)
        # We will update total_amount later based on items, or just set a dummy now
        order_values.append(f"({cust_id}, '{order_date.strftime('%Y-%m-%d %H:%M:%S')}', 0, '{status}')")
        
    sql += ",\n".join(order_values) + ";\n\n"

    # Insert Order Items (10000+)
    # Instead of a huge insert string at once, we'll break it into chunks if needed, but since it's a file, it's fine.
    sql += "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES\n"
    item_values = []
    for order_id in range(1, 5001):
        num_items = random.randint(1, 5)
        for _ in range(num_items):
            prod_id = random.randint(1, 210)
            qty = random.randint(1, 10)
            price = round(random.uniform(10.0, 1000.0), 2)
            item_values.append(f"({order_id}, {prod_id}, {qty}, {price})")
            
    sql += ",\n".join(item_values) + ";\n\n"
    
    # Update orders total_amount
    sql += "UPDATE orders o SET total_amount = (SELECT COALESCE(SUM(quantity * price), 0) FROM order_items oi WHERE oi.order_id = o.id);\n"

    with open('database/sample_data.sql', 'w') as f:
        f.write(sql)
        
if __name__ == '__main__':
    generate_sql()
    print("Generated database/sample_data.sql")
