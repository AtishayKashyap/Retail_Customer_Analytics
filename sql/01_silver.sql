CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;

-- ============================================================
-- BRONZE: source-grain ingestion
-- ============================================================

CREATE OR REPLACE TABLE bronze.customers AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_customers_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.orders AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_orders_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.order_items AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_order_items_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.products AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_products_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.sellers AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_sellers_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.payments AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_order_payments_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.reviews AS
SELECT *
FROM read_csv_auto(
    'data/raw/olist_order_reviews_dataset.csv',
    header = true,
    all_varchar = true
);

CREATE OR REPLACE TABLE bronze.category_translation AS
SELECT *
FROM read_csv_auto(
    'data/raw/product_category_name_translation.csv',
    header = true,
    all_varchar = true
);

-- ============================================================
-- SILVER: typed / normalized tables
-- ============================================================

CREATE OR REPLACE TABLE silver.customers AS
SELECT
    customer_id,
    customer_unique_id,
    try_cast(customer_zip_code_prefix AS INTEGER) AS customer_zip_code_prefix,
    customer_city,
    customer_state
FROM bronze.customers;

CREATE OR REPLACE TABLE silver.orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    try_cast(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
    try_cast(order_approved_at AS TIMESTAMP) AS order_approved_at,
    try_cast(order_delivered_carrier_date AS TIMESTAMP) AS order_delivered_carrier_date,
    try_cast(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
    try_cast(order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date
FROM bronze.orders;

CREATE OR REPLACE TABLE silver.order_items AS
SELECT
    order_id,
    try_cast(order_item_id AS INTEGER) AS order_item_id,
    product_id,
    seller_id,
    try_cast(shipping_limit_date AS TIMESTAMP) AS shipping_limit_date,
    try_cast(price AS DECIMAL(18,2)) AS price,
    try_cast(freight_value AS DECIMAL(18,2)) AS freight_value
FROM bronze.order_items;

CREATE OR REPLACE TABLE silver.products AS
SELECT
    product_id,
    product_category_name,
    try_cast(product_name_lenght AS INTEGER) AS product_name_length,
    try_cast(product_description_lenght AS INTEGER) AS product_description_length,
    try_cast(product_photos_qty AS INTEGER) AS product_photos_qty,
    try_cast(product_weight_g AS DOUBLE) AS product_weight_g,
    try_cast(product_length_cm AS DOUBLE) AS product_length_cm,
    try_cast(product_height_cm AS DOUBLE) AS product_height_cm,
    try_cast(product_width_cm AS DOUBLE) AS product_width_cm
FROM bronze.products;

CREATE OR REPLACE TABLE silver.sellers AS
SELECT
    seller_id,
    try_cast(seller_zip_code_prefix AS INTEGER) AS seller_zip_code_prefix,
    seller_city,
    seller_state
FROM bronze.sellers;

CREATE OR REPLACE TABLE silver.payments AS
SELECT
    order_id,
    try_cast(payment_sequential AS INTEGER) AS payment_sequential,
    payment_type,
    try_cast(payment_installments AS INTEGER) AS payment_installments,
    try_cast(payment_value AS DECIMAL(18,2)) AS payment_value
FROM bronze.payments;

CREATE OR REPLACE TABLE silver.reviews AS
SELECT
    review_id,
    order_id,
    try_cast(review_score AS INTEGER) AS review_score,
    try_cast(review_creation_date AS TIMESTAMP) AS review_creation_date,
    try_cast(review_answer_timestamp AS TIMESTAMP) AS review_answer_timestamp,
    review_comment_title,
    review_comment_message
FROM bronze.reviews;

CREATE OR REPLACE TABLE silver.category_translation AS
SELECT
    product_category_name,
    product_category_name_english
FROM bronze.category_translation;

CREATE OR REPLACE TABLE silver.order_review_summary AS
SELECT
    order_id,
    AVG(review_score) AS avg_review_score,
    COUNT(*) AS review_count
FROM silver.reviews
GROUP BY order_id;
