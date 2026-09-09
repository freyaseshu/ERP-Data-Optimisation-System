<<<<<<< HEAD
# ERP-Data-Optimisation-System
=======
# ERP Data Optimisation System

A full-stack academic/demo project that simulates an ERP environment and
provides tools to **analyse SQL queries, suggest optimisations, detect
duplicate data, archive old records, and monitor database performance.**

## Tech Stack

| Layer          | Technology                          |
|----------------|--------------------------------------|
| Frontend       | HTML5, CSS3, Bootstrap 5, Chart.js   |
| Backend        | Python 3, Flask                      |
| ORM            | SQLAlchemy (Flask-SQLAlchemy)        |
| Database       | MySQL 8+                             |
| Auth           | Flask session + Werkzeug password hashing |
| API testing    | Postman (collection not included — see API section) |

## Features

1. **Authentication** – login/logout, hashed passwords, role-based session (`Admin`, `Analyst`).
2. **Dashboard** – live stats cards + Chart.js graphs (before/after optimisation, execution time, resource usage).
3. **Database Analyser** – run `EXPLAIN` on predefined or custom `SELECT` queries; only safe read-only statements are allowed.
4. **Query Optimiser** – detects missing indexes, `SELECT *`, unnecessary `ORDER BY`, unindexed joins; suggests `CREATE INDEX` statements (only applied after explicit confirmation) and measures before/after execution time.
5. **Duplicate Data Checker** – finds duplicate customers/products/inventory/orders; lets you review and safely delete duplicates (confirmation required).
6. **Data Archive** – previews and archives old `orders` into `orders_archive` inside a transaction, logging every run to `archive_logs`.
7. **Performance Reports** – aggregated report (slowest/fastest queries, average improvement, duplicates found, records archived) with date-range filters and CSV export.

## Project Structure

```
erp-data-optimisation-system/
├── app.py                  # Flask application factory & entry point
├── config.py                # Env-based configuration
├── requirements.txt
├── .env.example              # Copy to .env and fill in your MySQL credentials
├── models/                   # SQLAlchemy models (one file per table)
├── routes/                   # Flask blueprints (one per module)
├── services/                 # Business logic (query analysis, optimisation, etc.)
├── templates/                # Jinja2 HTML templates (Bootstrap 5)
├── static/css, static/js     # Front-end assets
├── database/
│   ├── schema.sql             # DDL for all tables
│   ├── generate_sample_data.py  # Generates sample_data.sql
│   └── sample_data.sql        # ~515 customers, ~210 products, 5,000 orders, ~15,000 order_items
└── utils/                    # db.py (SQLAlchemy instance), decorators.py (auth guards)
```

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0+ running locally (or reachable over network)
- `pip`

### 2. Clone / unzip the project and install dependencies

```bash
cd erp-data-optimisation-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create the MySQL database

```sql
CREATE DATABASE erp_optimisation_db;
```

### 4. Configure environment variables

```bash
cp .env.example .env
# then edit .env with your MySQL username/password
```

### 5. Load the schema and sample data

```bash
mysql -u root -p erp_optimisation_db < database/schema.sql
mysql -u root -p erp_optimisation_db < database/sample_data.sql
```

> Sample data already includes two demo users:
> - `admin` / `Password123!` (role: Admin)
> - `analyst` / `Password123!` (role: Analyst)
>
> It also intentionally seeds ~15 duplicate customer emails, ~10 duplicate
> products, and a few duplicate inventory rows so the Duplicate Data
> Checker has real data to find.
>
> If you ever need to regenerate `sample_data.sql` (e.g. to change volume),
> run: `python database/generate_sample_data.py`

### 6. Run the application

```bash
python app.py
```

The app starts on `http://localhost:5000`. Log in with one of the demo
accounts above.

## API Reference

All endpoints (except `/api/auth/login`) require an active session.
Every response follows:

```json
{ "success": true, "message": "...", "data": {} }
```

| Method | Route                          | Description |
|--------|---------------------------------|--------------|
| POST   | `/api/auth/login`                | Log in |
| POST   | `/api/auth/logout`               | Log out |
| GET    | `/api/dashboard`                 | Dashboard stats |
| POST   | `/api/analyse-query`             | Run EXPLAIN + findings on a SELECT query |
| POST   | `/api/optimise-query`            | Get optimisation suggestions |
| POST   | `/api/create-index`              | Create a suggested index (requires confirmation on the frontend) |
| GET    | `/api/duplicates/<table_name>`   | Find duplicates in `customers`, `products`, `inventory`, or `orders` |
| POST   | `/api/duplicates/delete`         | Delete duplicate records (`confirm: true` required) |
| POST   | `/api/archive/preview`           | Preview how many records would be archived |
| POST   | `/api/archive/execute`           | Archive records (`confirm: true` required) |
| GET    | `/api/reports/performance`       | Aggregated performance report (`?range=today\|7days\|30days\|custom`) |
| GET    | `/api/reports/export`            | Download the report as CSV |

Import these routes into Postman manually, or generate a collection with
Postman's "Import from URL/OpenAPI" using the routes above as a guide.

## Security Notes

- The Database Analyser and Query Optimiser only ever accept `SELECT`
  (or `WITH ... SELECT`) statements — `DROP`, `DELETE`, `TRUNCATE`,
  `ALTER`, `INSERT`, `UPDATE`, and other destructive keywords are rejected
  before the query ever reaches MySQL.
- All dynamic SQL uses parameterised queries via SQLAlchemy's `text()`
  with bound parameters — no raw string formatting of user input into SQL.
- Index creation and record deletion/archiving require an explicit
  `confirm: true` flag from a confirmation modal in the UI; nothing
  destructive happens automatically.
- Passwords are hashed with Werkzeug's `generate_password_hash`
  (PBKDF2-SHA256 by default) — never stored in plain text.

## Notes on Realistic "Before/After" Numbers

Because this is a demo dataset on a local machine, raw millisecond timings
for a 5,000-row `orders` table can be too fast to show a dramatic
before/after difference. To make the effect of the suggested index more
visible for a demo/viva, `orders.customer_id` is intentionally **not**
indexed in `schema.sql` — the Query Optimiser will detect this and let you
create `idx_orders_customer_id` live from the UI.

## Extending

- To archive additional tables, add an entry to `ARCHIVABLE_TABLES` in
  `services/archive_service.py` and create a matching `<table>_archive`
  table (see `orders_archive` as a template).
- To add more duplicate-detection rules, extend `TABLE_CONFIG` in
  `services/duplicate_checker.py`.
>>>>>>> 2ab81b9 (Initial project setup)
