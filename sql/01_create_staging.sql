SET search_path=public;

CREATE TABLE stg_orders (
    order_id                        TEXT PRIMARY KEY,
    customer_id                     TEXT,
    order_status                    TEXT,
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP
);

CREATE TABLE stg_products (
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

CREATE TABLE stg_customers (
    customer_id               TEXT PRIMARY KEY,
    customer_unique_id        TEXT,
    customer_zip_code_prefix  TEXT,
    customer_city             TEXT,
    customer_state            TEXT
);

CREATE TABLE stg_order_revenue (
    order_id        TEXT,
    order_item_id   TEXT,
    product_id      TEXT,
    seller_id       TEXT,
    shipping_limit_date TIMESTAMP,
    price           NUMERIC,
    freight_value   NUMERIC,
    revenue         NUMERIC,
    PRIMARY KEY (order_id, order_item_id)
);