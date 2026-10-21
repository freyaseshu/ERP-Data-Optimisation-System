-- PostgreSQL schema generated from SQLAlchemy models. No database or data is dropped.


CREATE TABLE IF NOT EXISTS archive_logs (
	id SERIAL NOT NULL,
	table_name VARCHAR(50) NOT NULL,
	records_archived INTEGER NOT NULL,
	archive_date TIMESTAMP WITHOUT TIME ZONE,
	archived_by VARCHAR(50),
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS customers (
	id SERIAL NOT NULL,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(100) NOT NULL,
	city VARCHAR(100),
	customer_segment VARCHAR(50),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS departments (
	id SERIAL NOT NULL,
	name VARCHAR(100) NOT NULL,
	code VARCHAR(20) NOT NULL,
	budget NUMERIC(15, 2) NOT NULL,
	location VARCHAR(100),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (name),
	UNIQUE (code)
)

;


CREATE TABLE IF NOT EXISTS optimisation_recommendations (
	id SERIAL NOT NULL,
	query_text TEXT NOT NULL,
	recommendation_type VARCHAR(30) NOT NULL,
	title VARCHAR(150) NOT NULL,
	description TEXT NOT NULL,
	sql_statement TEXT,
	status VARCHAR(30) NOT NULL,
	applied_at TIMESTAMP WITHOUT TIME ZONE,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT recommendation_status_valid CHECK (status IN ('Pending','Applied','Rejected','Unsuccessful'))
)

;


CREATE TABLE IF NOT EXISTS orders_archive (
	id SERIAL NOT NULL,
	original_order_id INTEGER NOT NULL,
	customer_id INTEGER NOT NULL,
	order_date TIMESTAMP WITHOUT TIME ZONE,
	total_amount NUMERIC(12, 2),
	status VARCHAR(50),
	archived_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (original_order_id)
)

;


CREATE TABLE IF NOT EXISTS query_performance_logs (
	id SERIAL NOT NULL,
	query_text TEXT NOT NULL,
	query_name VARCHAR(150),
	status VARCHAR(30) NOT NULL,
	details JSON,
	execution_time_before NUMERIC(10, 6),
	execution_time_after NUMERIC(10, 6),
	optimization_applied TEXT,
	improvement_percentage NUMERIC(14, 2),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS suppliers (
	id SERIAL NOT NULL,
	name VARCHAR(100) NOT NULL,
	contact_name VARCHAR(100),
	email VARCHAR(100) NOT NULL,
	phone VARCHAR(30),
	city VARCHAR(100) NOT NULL,
	country VARCHAR(50) NOT NULL,
	rating NUMERIC(3, 2),
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (email)
)

;


CREATE TABLE IF NOT EXISTS system_limitations (
	id SERIAL NOT NULL,
	name VARCHAR(150) NOT NULL,
	problem TEXT NOT NULL,
	impact TEXT NOT NULL,
	solution TEXT NOT NULL,
	status VARCHAR(30) NOT NULL,
	test_evidence TEXT,
	remaining_work TEXT,
	updated_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id)
)

;


CREATE TABLE IF NOT EXISTS users (
	id SERIAL NOT NULL,
	username VARCHAR(50) NOT NULL,
	email VARCHAR(100) NOT NULL,
	password VARCHAR(255) NOT NULL,
	role VARCHAR(20) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	UNIQUE (username),
	UNIQUE (email),
	CONSTRAINT role_valid CHECK (role IN ('Admin', 'Analyst'))
)

;


CREATE TABLE IF NOT EXISTS employees (
	id SERIAL NOT NULL,
	department_id INTEGER,
	first_name VARCHAR(50) NOT NULL,
	last_name VARCHAR(50) NOT NULL,
	email VARCHAR(100) NOT NULL,
	role VARCHAR(50) NOT NULL,
	salary NUMERIC(12, 2) NOT NULL,
	hire_date DATE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL,
	UNIQUE (email)
)

;


CREATE TABLE IF NOT EXISTS products (
	id SERIAL NOT NULL,
	supplier_id INTEGER NOT NULL,
	sku VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	category VARCHAR(50),
	unit_price NUMERIC(12, 2) NOT NULL,
	cost_price NUMERIC(12, 2) NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id),
	UNIQUE (sku),
	CONSTRAINT product_prices_nonnegative CHECK (unit_price >= 0 AND cost_price >= 0)
)

;


CREATE TABLE IF NOT EXISTS inventory (
	id SERIAL NOT NULL,
	product_id INTEGER NOT NULL,
	quantity_on_hand INTEGER NOT NULL,
	reorder_level INTEGER NOT NULL,
	last_restocked_at TIMESTAMP WITHOUT TIME ZONE,
	warehouse_location VARCHAR(100),
	last_updated TIMESTAMP WITHOUT TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE,
	CONSTRAINT inventory_nonnegative CHECK (quantity_on_hand >= 0 AND reorder_level >= 0)
)

;


CREATE TABLE IF NOT EXISTS orders (
	id SERIAL NOT NULL,
	customer_id INTEGER NOT NULL,
	employee_id INTEGER,
	shipping_city VARCHAR(100),
	order_date TIMESTAMP WITHOUT TIME ZONE,
	total_amount NUMERIC(14, 2) NOT NULL,
	status VARCHAR(30) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE CASCADE,
	FOREIGN KEY(employee_id) REFERENCES employees (id),
	CONSTRAINT order_amount_nonnegative CHECK (total_amount >= 0),
	CONSTRAINT order_status_valid CHECK (status IN ('Pending','Processing','Shipped','Delivered','Cancelled'))
)

;


CREATE TABLE IF NOT EXISTS order_items (
	id SERIAL NOT NULL,
	order_id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	quantity INTEGER NOT NULL,
	unit_price NUMERIC(12, 2) NOT NULL,
	discount NUMERIC(4, 2) NOT NULL,
	line_total NUMERIC(14, 2) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE,
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE,
	CONSTRAINT item_amount_valid CHECK (quantity > 0 AND unit_price >= 0 AND discount >= 0 AND discount <= 1 AND line_total >= 0)
)

;


CREATE TABLE IF NOT EXISTS payments (
	id SERIAL NOT NULL,
	order_id INTEGER NOT NULL,
	payment_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	payment_method VARCHAR(50) NOT NULL,
	payment_status VARCHAR(30) NOT NULL,
	transaction_ref VARCHAR(100) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE,
	UNIQUE (transaction_ref),
	CONSTRAINT payment_nonnegative CHECK (amount >= 0)
)

;


CREATE TABLE IF NOT EXISTS transactions (
	id SERIAL NOT NULL,
	payment_id INTEGER,
	account_code VARCHAR(30) NOT NULL,
	transaction_type VARCHAR(20) NOT NULL,
	amount NUMERIC(12, 2) NOT NULL,
	transaction_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	status VARCHAR(30) NOT NULL,
	description TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE SET NULL,
	CONSTRAINT transaction_nonnegative CHECK (amount >= 0)
)

;
