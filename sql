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

WITH

revenue_check AS (
    SELECT
        SUM(f.revenue) AS fact_total_revenue,
        SUM(oi.price + oi.freight_value) AS stg_total_revenue
    FROM fact_orders f
    JOIN stg_order_revenue oi 
      ON f.order_id = oi.order_id 
     AND f.order_item_id = oi.order_item_id::INT
),


order_count_check AS (
    SELECT
        (SELECT COUNT(DISTINCT order_id) FROM fact_orders) AS fact_order_count,
        (SELECT COUNT(DISTINCT order_id) FROM stg_orders) AS stg_order_count,
        (SELECT COUNT(*) FROM fact_orders) AS fact_order_items_count,
        (SELECT COUNT(*) FROM stg_order_revenue) AS stg_order_items_count
),


duplicate_pk_check AS (
    SELECT COUNT(*) AS duplicate_pk_count
    FROM (
        SELECT order_id, order_item_id, COUNT(*) AS cnt
        FROM fact_orders
        GROUP BY order_id, order_item_id
        HAVING COUNT(*) > 1
    ) sub
),


fk_check AS (
    SELECT
        (SELECT COUNT(*) 
         FROM fact_orders f 
         LEFT JOIN dim_customers c ON f.customer_key = c.customer_key 
         WHERE c.customer_key IS NULL) AS invalid_customer_fk,
         
        (SELECT COUNT(*) 
         FROM fact_orders f 
         LEFT JOIN dim_products p ON f.product_key = p.product_key 
         WHERE p.product_key IS NULL) AS invalid_product_fk,
         
        (SELECT COUNT(*) 
         FROM fact_orders f 
         LEFT JOIN dim_date d ON f.date_key = d.date_key 
         WHERE d.date_key IS NULL) AS invalid_date_fk
)

SELECT
    rc.fact_total_revenue,
    rc.stg_total_revenue,
    occ.fact_order_count,
    occ.stg_order_count,
    occ.fact_order_items_count,
    occ.stg_order_items_count,
    dpk.duplicate_pk_count,
    fk.invalid_customer_fk,
    fk.invalid_product_fk,
    fk.invalid_date_fk
FROM revenue_check rc
CROSS JOIN order_count_check occ
CROSS JOIN duplicate_pk_check dpk
CROSS JOIN fk_check fk;
