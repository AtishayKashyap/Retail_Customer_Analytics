-- Bronze: raw files loaded as text, so a malformed value can be counted instead of failing the load.
-- Silver: typed columns. try_cast turns bad values into NULL; 04_quality.sql counts every such NULL.
-- {raw_dir} is substituted (and quote-escaped) by build.py.

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;

CREATE OR REPLACE TABLE bronze.customers AS
SELECT * FROM read_csv('{raw_dir}/olist_customers_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.orders AS
SELECT * FROM read_csv('{raw_dir}/olist_orders_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.order_items AS
SELECT * FROM read_csv('{raw_dir}/olist_order_items_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.products AS
SELECT * FROM read_csv('{raw_dir}/olist_products_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.sellers AS
SELECT * FROM read_csv('{raw_dir}/olist_sellers_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.payments AS
SELECT * FROM read_csv('{raw_dir}/olist_order_payments_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.reviews AS
SELECT * FROM read_csv('{raw_dir}/olist_order_reviews_dataset.csv', header = true, all_varchar = true);
CREATE OR REPLACE TABLE bronze.category_translation AS
SELECT * FROM read_csv('{raw_dir}/product_category_name_translation.csv', header = true, all_varchar = true);

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
    try_cast(order_purchase_timestamp AS TIMESTAMP)      AS purchased_at,
    try_cast(order_approved_at AS TIMESTAMP)             AS approved_at,
    try_cast(order_delivered_carrier_date AS TIMESTAMP)  AS delivered_to_carrier_at,
    try_cast(order_delivered_customer_date AS TIMESTAMP) AS delivered_at,
    -- Olist stores the promised date as midnight of that day; it is a date, not a deadline to the second.
    try_cast(order_estimated_delivery_date AS TIMESTAMP)::DATE AS estimated_delivery_date
FROM bronze.orders;

CREATE OR REPLACE TABLE silver.order_items AS
SELECT
    order_id,
    try_cast(order_item_id AS INTEGER)        AS order_item_id,
    product_id,
    seller_id,
    try_cast(shipping_limit_date AS TIMESTAMP) AS shipping_limit_at,
    try_cast(price AS DECIMAL(18, 2))          AS price,
    try_cast(freight_value AS DECIMAL(18, 2))  AS freight_value
FROM bronze.order_items;

CREATE OR REPLACE TABLE silver.products AS
SELECT
    product_id,
    product_category_name,
    -- the source misspells "length"
    try_cast(product_name_lenght AS INTEGER)        AS product_name_length,
    try_cast(product_description_lenght AS INTEGER) AS product_description_length,
    try_cast(product_photos_qty AS INTEGER)         AS product_photos_qty,
    try_cast(product_weight_g AS DOUBLE)            AS product_weight_g
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
    try_cast(payment_sequential AS INTEGER)   AS payment_sequential,
    payment_type,
    try_cast(payment_installments AS INTEGER) AS payment_installments,
    try_cast(payment_value AS DECIMAL(18, 2)) AS payment_value
FROM bronze.payments;

CREATE OR REPLACE TABLE silver.reviews AS
SELECT
    review_id,
    order_id,
    try_cast(review_score AS INTEGER)              AS review_score,
    try_cast(review_creation_date AS TIMESTAMP)    AS review_created_at,
    try_cast(review_answer_timestamp AS TIMESTAMP) AS review_answered_at
FROM bronze.reviews;

CREATE OR REPLACE TABLE silver.category_translation AS
SELECT product_category_name, product_category_name_english
FROM bronze.category_translation;
