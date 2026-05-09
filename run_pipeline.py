"""
run_pipeline.py
===============
Olist E-Commerce  –  fully automatic end-to-end pipeline

HOW TO RUN (nothing else needed):
    python run_pipeline.py

What this script does automatically:
  1. Installs all missing Python packages
  2. Downloads the Olist dataset (Kaggle if available, direct URL otherwise)
  3. Cleans and transforms every dataset
  4. Creates a local PostgreSQL database + star schema
  5. Loads all data
  6. Validates integrity
  7. Power BI connects to localhost / db=olist / user=postgres
"""

# ── bootstrap: install packages before any imports ──────────────────────────
import subprocess, sys

REQUIRED = [
    "pandas", "psycopg2-binary", "requests", "kaggle", "tqdm"
]

def install_missing():
    import importlib
    missing = []
    CHECK = {
        "psycopg2-binary": "psycopg2",
        "kaggle":          "kaggle",
        "pandas":          "pandas",
        "requests":        "requests",
        "tqdm":            "tqdm",
    }
    for pkg, imp in CHECK.items():
        try:
            importlib.import_module(imp)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[SETUP] Installing: {', '.join(missing)} ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing
        )
        print("[SETUP] Packages installed.\n")

install_missing()

# ── real imports ─────────────────────────────────────────────────────────────
import os, io, time, zipfile, platform, textwrap
from pathlib import Path

import pandas as pd
import psycopg2
import requests
from psycopg2.extras import execute_values

# ── paths ────────────────────────────────────────────────────────────────────
BASE           = Path(__file__).parent
RAW_PATH       = BASE / "data" / "raw"
PROCESSED_PATH = BASE / "data" / "processed"

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"

# Direct-download fallback (public mirror, no login needed)
DIRECT_URL = (
    "https://github.com/erkansirin78/datasets/raw/master/"
    "brazilian-ecommerce.zip"
)

# ── logging ──────────────────────────────────────────────────────────────────
def log(step, msg):
    print(f"  [{step:<10}] {msg}")

def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")

# ────────────────────────────────────────────────────────────────────────────
#  STEP 0  –  CONNECT TO POSTGRESQL
# ────────────────────────────────────────────────────────────────────────────
DEFAULT_PASSWORDS = ["", "postgres", "admin", "root", "password"]

def detect_pg_config():
    """
    First tries common default credentials silently.
    If none work, asks the user for host, username, and password.
    Returns a working config dict.
    """
    import getpass

    log("DB-DETECT", "Finding PostgreSQL credentials...")

    # Try all default combos silently first
    for pw in DEFAULT_PASSWORDS:
        cfg = dict(host="localhost", port=5432,
                   dbname="postgres", user="postgres", password=pw)
        try:
            conn = psycopg2.connect(**cfg)
            conn.close()
            log("DB-DETECT", f"Connected  (password={'<empty>' if pw=='' else '***'})")
            _ensure_db(cfg, "olist")
            return {**cfg, "dbname": "olist"}
        except psycopg2.OperationalError:
            continue

    # Defaults didn't work — ask the user
    print()
    print("  Could not connect with default credentials.")
    print("  Please enter your PostgreSQL connection details.")
    print("  (press Enter to keep the default shown in brackets)\n")

    host_input = input("  Host       [default: localhost]: ").strip()
    host = host_input if host_input else "localhost"

    port_input = input("  Port       [default: 5432]: ").strip()
    port = int(port_input) if port_input else 5432

    user_input = input("  Username   [default: postgres]: ").strip()
    user = user_input if user_input else "postgres"

    print()
    for attempt in range(3):
        pw = getpass.getpass("  Password (hidden): ")
        cfg = dict(host=host, port=port,
                   dbname="postgres", user=user, password=pw)
        try:
            conn = psycopg2.connect(**cfg)
            conn.close()
            log("DB-DETECT", f"Connected as '{user}' on {host}:{port}")
            _ensure_db(cfg, "olist")
            return {**cfg, "dbname": "olist"}
        except psycopg2.OperationalError:
            remaining = 2 - attempt
            if remaining > 0:
                print(f"  Incorrect password. {remaining} attempt(s) left.\n")
            else:
                raise RuntimeError(textwrap.dedent("""
                    Could not connect to PostgreSQL after 3 attempts.
                    Please check that:
                      • PostgreSQL is running
                      • The username and host are correct
                      • The password you entered is correct
                """))


def _ensure_db(admin_cfg, dbname):
    """Create target database if it doesn't exist."""
    conn = psycopg2.connect(**admin_cfg)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{dbname}"')
            log("DB-DETECT", f"Created database '{dbname}'")
        else:
            log("DB-DETECT", f"Database '{dbname}' already exists")
    conn.close()


# ────────────────────────────────────────────────────────────────────────────
#  STEP 1  –  DOWNLOAD DATA
# ────────────────────────────────────────────────────────────────────────────
EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_items_dataset.csv",
]

def data_already_present():
    return all((RAW_PATH / f).exists() for f in EXPECTED_FILES)


def download_via_kaggle():
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        RAW_PATH.mkdir(parents=True, exist_ok=True)
        log("DOWNLOAD", "Kaggle credentials found – downloading...")
        api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_PATH), unzip=True)
        log("DOWNLOAD", "Kaggle download complete.")
        return True
    except Exception as e:
        log("DOWNLOAD", f"Kaggle unavailable ({type(e).__name__}) – trying fallback...")
        return False


def download_via_direct():
    log("DOWNLOAD", "Downloading from public mirror (no login needed)...")
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(DIRECT_URL, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        buf = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            buf.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = downloaded / total * 100
                print(f"\r    {pct:5.1f}%  ({downloaded//1024//1024} MB)", end="", flush=True)
        print()
        buf.seek(0)
        with zipfile.ZipFile(buf) as z:
            z.extractall(RAW_PATH)
        log("DOWNLOAD", "Direct download complete.")
        return True
    except Exception as e:
        log("DOWNLOAD", f"Direct download failed: {e}")
        return False


def download_data():
    if data_already_present():
        log("DOWNLOAD", "Raw data already present – skipping download.")
        return
    if not download_via_kaggle():
        if not download_via_direct():
            raise RuntimeError(
                "Could not download data via Kaggle or direct URL.\n"
                "Please place the Olist CSV files in:  data/raw/"
            )


# ────────────────────────────────────────────────────────────────────────────
#  STEP 2  –  CLEAN & TRANSFORM
# ────────────────────────────────────────────────────────────────────────────
def clean_customers():
    df = pd.read_csv(RAW_PATH / "olist_customers_dataset.csv")
    df = df.drop_duplicates(subset="customer_id")
    df["customer_city"] = df["customer_city"].str.strip().str.title()
    df["customer_zip_code_prefix"] = (
        df["customer_zip_code_prefix"].astype(str).str.zfill(5)
    )
    df.to_csv(PROCESSED_PATH / "customers_clean.csv", index=False)
    log("CLEAN", f"customers       → {len(df):,} rows")
    return df


def clean_orders():
    df = pd.read_csv(RAW_PATH / "olist_orders_dataset.csv")
    df = df.drop_duplicates(subset="order_id")
    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df[
        df["order_delivered_customer_date"].isna() |
        (df["order_delivered_customer_date"] >= df["order_purchase_timestamp"])
    ]
    df.to_csv(PROCESSED_PATH / "orders_clean.csv", index=False)
    log("CLEAN", f"orders          → {len(df):,} rows")
    return df


def clean_products():
    df = pd.read_csv(RAW_PATH / "olist_products_dataset.csv", encoding="utf-8")
    df = df.drop_duplicates(subset="product_id")
    df = df[
        (df["product_weight_g"] > 0) & (df["product_length_cm"] > 0) &
        (df["product_height_cm"] > 0) & (df["product_width_cm"] > 0)
    ]
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    numeric_cols = [
        "product_name_lenght", "product_description_lenght", "product_photos_qty",
        "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm",
    ]
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.replace(",", ".").astype(float)
    df.to_csv(PROCESSED_PATH / "products_clean.csv", index=False, encoding="utf-8")
    log("CLEAN", f"products        → {len(df):,} rows")
    return df


def clean_order_items():
    df = pd.read_csv(RAW_PATH / "olist_order_items_dataset.csv")
    df = df.drop_duplicates(subset=["order_id", "order_item_id"])
    df = df[(df["price"] >= 0) & (df["freight_value"] >= 0)]
    df["shipping_limit_date"] = pd.to_datetime(
        df["shipping_limit_date"], errors="coerce"
    )
    df["revenue"] = df["price"] + df["freight_value"]
    df.to_csv(PROCESSED_PATH / "order_items_clean.csv", index=False)
    log("CLEAN", f"order_items     → {len(df):,} rows")
    return df


def clean_all():
    PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    c  = clean_customers()
    o  = clean_orders()
    p  = clean_products()
    oi = clean_order_items()
    return c, o, p, oi


# ────────────────────────────────────────────────────────────────────────────
#  STEP 3  –  DDL (idempotent)
# ────────────────────────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT,
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT
);
CREATE TABLE IF NOT EXISTS stg_orders (
    order_id                       TEXT PRIMARY KEY,
    customer_id                    TEXT,
    order_status                   TEXT,
    order_purchase_timestamp       TIMESTAMP,
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP
);
CREATE TABLE IF NOT EXISTS stg_products (
    product_id                 TEXT PRIMARY KEY,
    product_category_name      TEXT,
    product_name_lenght        NUMERIC,
    product_description_lenght NUMERIC,
    product_photos_qty         NUMERIC,
    product_weight_g           NUMERIC,
    product_length_cm          NUMERIC,
    product_height_cm          NUMERIC,
    product_width_cm           NUMERIC
);
CREATE TABLE IF NOT EXISTS stg_order_revenue (
    order_id            TEXT,
    order_item_id       TEXT,
    product_id          TEXT,
    seller_id           TEXT,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC,
    freight_value       NUMERIC,
    revenue             NUMERIC,
    PRIMARY KEY (order_id, order_item_id)
);
CREATE TABLE IF NOT EXISTS dim_customers (
    customer_key             SERIAL PRIMARY KEY,
    customer_id              VARCHAR(50) NOT NULL UNIQUE,
    customer_unique_id       VARCHAR(50),
    customer_zip_code_prefix INT,
    customer_city            VARCHAR(100),
    customer_state           VARCHAR(10)
);
CREATE TABLE IF NOT EXISTS dim_products (
    product_key                SERIAL PRIMARY KEY,
    product_id                 VARCHAR(50) NOT NULL UNIQUE,
    product_category_name      VARCHAR(100),
    product_name_lenght        INT,
    product_description_lenght INT,
    product_photos_qty         INT,
    product_weight_g           INT,
    product_length_cm          INT,
    product_height_cm          INT,
    product_width_cm           INT
);
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    DATE PRIMARY KEY,
    year        INT,
    quarter     INT,
    month       INT,
    day         INT,
    day_of_week INT
);
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id                       VARCHAR(50) NOT NULL,
    order_item_id                  INT NOT NULL,
    customer_key                   INT NOT NULL,
    product_key                    INT NOT NULL,
    date_key                       DATE NOT NULL,
    order_status                   VARCHAR(50),
    order_approved_at              TIMESTAMP,
    order_delivered_carrier_date   TIMESTAMP,
    order_delivered_customer_date  TIMESTAMP,
    order_estimated_delivery_date  TIMESTAMP,
    revenue                        NUMERIC(12,2),
    price                          NUMERIC(12,2),
    freight                        NUMERIC(12,2),
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key),
    FOREIGN KEY (product_key)  REFERENCES dim_products(product_key),
    FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
);
"""

def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()
    log("DB", "All tables created / verified.")


# ────────────────────────────────────────────────────────────────────────────
#  STEP 4  –  LOAD STAGING
# ────────────────────────────────────────────────────────────────────────────
def _truncate(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    conn.commit()


def _safe_val(v):
    """Convert NaT / nan to None so psycopg2 never sees them."""
    try:
        if pd.isnull(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _load(conn, table, df, cols, insert_sql):
    _truncate(conn, table)
    sub = df[cols].where(pd.notna(df[cols]), other=None)
    rows = [tuple(_safe_val(v) for v in r) for r in sub.itertuples(index=False)]
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, rows)
    conn.commit()
    log("LOAD", f"{table:<25} {len(rows):>8,} rows")


def load_staging(conn, customers, orders, products, order_items):
    _load(conn, "stg_customers", customers,
          ["customer_id","customer_unique_id","customer_zip_code_prefix",
           "customer_city","customer_state"],
          "INSERT INTO stg_customers VALUES %s ON CONFLICT DO NOTHING")

    _load(conn, "stg_orders", orders,
          ["order_id","customer_id","order_status","order_purchase_timestamp",
           "order_approved_at","order_delivered_carrier_date",
           "order_delivered_customer_date","order_estimated_delivery_date"],
          "INSERT INTO stg_orders VALUES %s ON CONFLICT DO NOTHING")

    _load(conn, "stg_products", products,
          ["product_id","product_category_name","product_name_lenght",
           "product_description_lenght","product_photos_qty","product_weight_g",
           "product_length_cm","product_height_cm","product_width_cm"],
          "INSERT INTO stg_products VALUES %s ON CONFLICT DO NOTHING")

    _load(conn, "stg_order_revenue", order_items,
          ["order_id","order_item_id","product_id","seller_id",
           "shipping_limit_date","price","freight_value","revenue"],
          "INSERT INTO stg_order_revenue VALUES %s ON CONFLICT DO NOTHING")


# ────────────────────────────────────────────────────────────────────────────
#  STEP 5  –  STAR SCHEMA
# ────────────────────────────────────────────────────────────────────────────
DIM_SQL = """
INSERT INTO dim_customers (
    customer_id, customer_unique_id, customer_zip_code_prefix,
    customer_city, customer_state
)
SELECT customer_id, customer_unique_id, customer_zip_code_prefix::INT,
       customer_city, customer_state
FROM stg_customers
ON CONFLICT (customer_id) DO UPDATE SET
    customer_unique_id       = EXCLUDED.customer_unique_id,
    customer_zip_code_prefix = EXCLUDED.customer_zip_code_prefix,
    customer_city            = EXCLUDED.customer_city,
    customer_state           = EXCLUDED.customer_state;

INSERT INTO dim_products (
    product_id, product_category_name, product_name_lenght,
    product_description_lenght, product_photos_qty,
    product_weight_g, product_length_cm, product_height_cm, product_width_cm
)
SELECT DISTINCT product_id, product_category_name,
    product_name_lenght::INT, product_description_lenght::INT,
    product_photos_qty::INT, product_weight_g::INT,
    product_length_cm::INT, product_height_cm::INT, product_width_cm::INT
FROM stg_products
ON CONFLICT (product_id) DO UPDATE SET
    product_category_name      = EXCLUDED.product_category_name,
    product_name_lenght        = EXCLUDED.product_name_lenght,
    product_description_lenght = EXCLUDED.product_description_lenght,
    product_photos_qty         = EXCLUDED.product_photos_qty,
    product_weight_g           = EXCLUDED.product_weight_g,
    product_length_cm          = EXCLUDED.product_length_cm,
    product_height_cm          = EXCLUDED.product_height_cm,
    product_width_cm           = EXCLUDED.product_width_cm;

INSERT INTO dim_date (date_key, year, quarter, month, day, day_of_week)
SELECT DISTINCT
    order_purchase_timestamp::DATE,
    EXTRACT(YEAR    FROM order_purchase_timestamp)::INT,
    EXTRACT(QUARTER FROM order_purchase_timestamp)::INT,
    EXTRACT(MONTH   FROM order_purchase_timestamp)::INT,
    EXTRACT(DAY     FROM order_purchase_timestamp)::INT,
    EXTRACT(DOW     FROM order_purchase_timestamp)::INT
FROM stg_orders
WHERE order_purchase_timestamp IS NOT NULL
ON CONFLICT (date_key) DO NOTHING;
"""

FACT_SQL = """
DELETE FROM fact_orders
WHERE (order_id, order_item_id::TEXT) IN (
    SELECT order_id, order_item_id FROM stg_order_revenue
);

INSERT INTO fact_orders (
    order_id, order_item_id, customer_key, product_key, date_key,
    order_status, order_approved_at, order_delivered_carrier_date,
    order_delivered_customer_date, order_estimated_delivery_date,
    revenue, price, freight
)
SELECT
    oi.order_id,
    oi.order_item_id::INT,
    dc.customer_key,
    dp.product_key,
    o.order_purchase_timestamp::DATE,
    o.order_status,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    (oi.price + oi.freight_value)::NUMERIC(12,2),
    oi.price::NUMERIC(12,2),
    oi.freight_value::NUMERIC(12,2)
FROM stg_order_revenue oi
JOIN stg_orders    o  ON oi.order_id   = o.order_id
JOIN dim_customers dc ON o.customer_id = dc.customer_id
JOIN dim_products  dp ON oi.product_id = dp.product_id;
"""


def populate_star_schema(conn):
    with conn.cursor() as cur:
        cur.execute(DIM_SQL)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(FACT_SQL)
    conn.commit()

    with conn.cursor() as cur:
        for tbl in ["dim_customers","dim_products","dim_date","fact_orders"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            log("SCHEMA", f"{tbl:<25} {cur.fetchone()[0]:>8,} rows")


# ────────────────────────────────────────────────────────────────────────────
#  STEP 6  –  VALIDATION
# ────────────────────────────────────────────────────────────────────────────
CHECKS = {
    "Orphan facts – no customer":
        "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_customers dc ON f.customer_key=dc.customer_key WHERE dc.customer_key IS NULL",
    "Orphan facts – no product":
        "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_products dp ON f.product_key=dp.product_key WHERE dp.product_key IS NULL",
    "Orphan facts – no date":
        "SELECT COUNT(*) FROM fact_orders f LEFT JOIN dim_date d ON f.date_key=d.date_key WHERE d.date_key IS NULL",
    "Negative revenue":
        "SELECT COUNT(*) FROM fact_orders WHERE revenue < 0",
    "NULL order_id":
        "SELECT COUNT(*) FROM fact_orders WHERE order_id IS NULL",
}

def validate(conn):
    all_ok = True
    with conn.cursor() as cur:
        for label, sql in CHECKS.items():
            cur.execute(sql)
            n = cur.fetchone()[0]
            status = "✓ OK" if n == 0 else f"⚠  {n} rows"
            log("VALIDATE", f"{label:<30} {status}")
            if n > 0:
                all_ok = False
    return all_ok


# ────────────────────────────────────────────────────────────────────────────
#  POWER BI CONNECTION REMINDER
# ────────────────────────────────────────────────────────────────────────────
def print_powerbi_info(cfg):
    print(f"""
┌─────────────────────────────────────────────────┐
│          Power BI Connection Details             │
├─────────────────────────────────────────────────┤
│  Server   :  {cfg['host']:<35} │
│  Port     :  {str(cfg['port']):<35} │
│  Database :  {cfg['dbname']:<35} │
│  User     :  {cfg['user']:<35} │
│  Mode     :  DirectQuery  (auto-refresh)         │
└─────────────────────────────────────────────────┘
""")


# ────────────────────────────────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    print("=" * 55)
    print("  Olist E-Commerce Pipeline  –  starting")
    print(f"  Python {sys.version.split()[0]}  |  {platform.system()} {platform.release()}")
    print("=" * 55)

    section("STEP 1 / 6  –  Download data")
    download_data()

    section("STEP 2 / 6  –  Clean & transform")
    customers, orders, products, order_items = clean_all()

    section("STEP 3 / 6  –  Connect to PostgreSQL")
    db_cfg = detect_pg_config()
    conn   = psycopg2.connect(**db_cfg)

    section("STEP 4 / 6  –  Create tables")
    create_tables(conn)

    section("STEP 5 / 6  –  Load staging tables")
    load_staging(conn, customers, orders, products, order_items)

    section("STEP 5b/ 6  –  Build star schema")
    populate_star_schema(conn)

    section("STEP 6 / 6  –  Validate")
    ok = validate(conn)
    conn.close()

    elapsed = time.time() - t0
    print()
    print("=" * 55)
    if ok:
        print(f"  ✓  Pipeline complete in {elapsed:.1f}s  –  all checks passed")
    else:
        print(f"  ⚠  Pipeline complete in {elapsed:.1f}s  –  review warnings above")
    print("=" * 55)

    print_powerbi_info(db_cfg)


if __name__ == "__main__":
    main()