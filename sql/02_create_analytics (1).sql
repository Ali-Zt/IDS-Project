DROP TABLE IF EXISTS dim_customers CASCADE;

CREATE TABLE dim_customers (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL UNIQUE,
    customer_unique_id VARCHAR(50),
    customer_zip_code_prefix INT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(10)
);

DROP TABLE IF EXISTS dim_products CASCADE;

CREATE TABLE dim_products (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_category_name VARCHAR(100),
    product_name_lenght INT,
    product_description_lenght INT,
    product_photos_qty INT,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);

DROP TABLE IF EXISTS dim_date CASCADE;

CREATE TABLE dim_date (
    date_key DATE PRIMARY KEY,
    year INT,
    quarter INT,
    month INT,
    day INT,
    day_of_week INT
);

INSERT INTO dim_customers (
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
)
SELECT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix::INT,  -- cast text to integer
    customer_city,
    customer_state
FROM stg_customers;

INSERT INTO dim_products (
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
)
SELECT DISTINCT
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
FROM stg_products;

INSERT INTO dim_date (
    date_key,
    year,
    quarter,
    month,
    day,
    day_of_week
)
SELECT DISTINCT
    order_purchase_timestamp::DATE AS date_key,
    EXTRACT(YEAR FROM order_purchase_timestamp),
    EXTRACT(QUARTER FROM order_purchase_timestamp),
    EXTRACT(MONTH FROM order_purchase_timestamp),
    EXTRACT(DAY FROM order_purchase_timestamp),
    EXTRACT(DOW FROM order_purchase_timestamp)
FROM stg_orders
WHERE order_purchase_timestamp IS NOT NULL;

DROP TABLE IF EXISTS fact_orders;

CREATE TABLE fact_orders (
    order_id VARCHAR(50) NOT NULL,
    order_item_id INT NOT NULL,
    customer_key INT NOT NULL,
    product_key INT NOT NULL,
    date_key DATE NOT NULL,

    order_status VARCHAR(50),
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,

    revenue NUMERIC(12,2),
    price NUMERIC(12,2),
    freight NUMERIC(12,2),

    PRIMARY KEY (order_id, order_item_id),

    FOREIGN KEY (customer_key) REFERENCES dim_customers(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_products(product_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

INSERT INTO fact_orders (
    order_id,
    order_item_id,
    customer_key,
    product_key,
    date_key,
    order_status,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    revenue,
    price,
    freight
)
SELECT
    oi.order_id,
    oi.order_item_id::INT,
    dc.customer_key,
    dp.product_key,
    o.order_purchase_timestamp::DATE AS date_key,
    o.order_status,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    (oi.price + oi.freight_value)::NUMERIC(12,2) AS revenue,
    oi.price::NUMERIC(12,2) AS price,
    oi.freight_value::NUMERIC(12,2) AS freight
FROM stg_order_revenue oi
JOIN stg_orders o 
    ON oi.order_id = o.order_id
JOIN dim_customers dc 
    ON o.customer_id = dc.customer_id
JOIN dim_products dp 
    ON oi.product_id = dp.product_id;