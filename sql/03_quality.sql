CREATE SCHEMA IF NOT EXISTS quality;

-- ============================================================
-- 1. Row-count reconciliation
-- ============================================================

CREATE OR REPLACE TABLE quality.row_counts AS
SELECT 'silver.customers' AS table_name, COUNT(*) AS row_count
FROM silver.customers

UNION ALL

SELECT 'silver.orders', COUNT(*)
FROM silver.orders

UNION ALL

SELECT 'silver.order_items', COUNT(*)
FROM silver.order_items

UNION ALL

SELECT 'silver.products', COUNT(*)
FROM silver.products

UNION ALL

SELECT 'silver.sellers', COUNT(*)
FROM silver.sellers

UNION ALL

SELECT 'silver.payments', COUNT(*)
FROM silver.payments

UNION ALL

SELECT 'silver.reviews', COUNT(*)
FROM silver.reviews;


-- ============================================================
-- 2. Null / required-field checks
-- ============================================================

CREATE OR REPLACE TABLE quality.required_field_checks AS
SELECT
    'orders.order_id' AS check_name,
    COUNT(*) FILTER (WHERE order_id IS NULL) AS failed_rows
FROM silver.orders

UNION ALL

SELECT
    'orders.customer_id',
    COUNT(*) FILTER (WHERE customer_id IS NULL)
FROM silver.orders

UNION ALL

SELECT
    'customers.customer_unique_id',
    COUNT(*) FILTER (WHERE customer_unique_id IS NULL)
FROM silver.customers

UNION ALL

SELECT
    'order_items.order_id',
    COUNT(*) FILTER (WHERE order_id IS NULL)
FROM silver.order_items

UNION ALL

SELECT
    'order_items.product_id',
    COUNT(*) FILTER (WHERE product_id IS NULL)
FROM silver.order_items;


-- ============================================================
-- 3. Duplicate-key checks
-- ============================================================

CREATE OR REPLACE TABLE quality.duplicate_key_checks AS
SELECT
    'customers.customer_id' AS check_name,
    COUNT(*) - COUNT(DISTINCT customer_id) AS duplicate_rows
FROM silver.customers

UNION ALL

SELECT
    'orders.order_id',
    COUNT(*) - COUNT(DISTINCT order_id)
FROM silver.orders

UNION ALL

SELECT
    'products.product_id',
    COUNT(*) - COUNT(DISTINCT product_id)
FROM silver.products

UNION ALL

SELECT
    'sellers.seller_id',
    COUNT(*) - COUNT(DISTINCT seller_id)
FROM silver.sellers;


-- ============================================================
-- 4. Referential-integrity checks
-- ============================================================

CREATE OR REPLACE TABLE quality.referential_integrity_checks AS
SELECT
    'orders -> customers' AS check_name,
    COUNT(*) AS orphan_rows
FROM silver.orders o
LEFT JOIN silver.customers c
    ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL

UNION ALL

SELECT
    'order_items -> orders',
    COUNT(*)
FROM silver.order_items oi
LEFT JOIN silver.orders o
    ON oi.order_id = o.order_id
WHERE o.order_id IS NULL

UNION ALL

SELECT
    'order_items -> products',
    COUNT(*)
FROM silver.order_items oi
LEFT JOIN silver.products p
    ON oi.product_id = p.product_id
WHERE p.product_id IS NULL

UNION ALL

SELECT
    'order_items -> sellers',
    COUNT(*)
FROM silver.order_items oi
LEFT JOIN silver.sellers s
    ON oi.seller_id = s.seller_id
WHERE s.seller_id IS NULL;


-- ============================================================
-- 5. Order chronology checks
-- ============================================================

CREATE OR REPLACE TABLE quality.chronology_checks AS
SELECT
    'delivered_before_purchase' AS check_name,
    COUNT(*) AS failed_rows
FROM silver.orders
WHERE order_delivered_customer_date IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL
  AND order_delivered_customer_date < order_purchase_timestamp

UNION ALL

SELECT
    'carrier_after_customer_delivery',
    COUNT(*)
FROM silver.orders
WHERE order_delivered_carrier_date IS NOT NULL
  AND order_delivered_customer_date IS NOT NULL
  AND order_delivered_carrier_date > order_delivered_customer_date

UNION ALL

SELECT
    'approved_before_purchase',
    COUNT(*)
FROM silver.orders
WHERE order_approved_at IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL
  AND order_approved_at < order_purchase_timestamp;


-- ============================================================
-- 6. Negative monetary-value checks
-- ============================================================

CREATE OR REPLACE TABLE quality.monetary_checks AS
SELECT
    'negative_item_price' AS check_name,
    COUNT(*) AS failed_rows
FROM silver.order_items
WHERE price < 0

UNION ALL

SELECT
    'negative_freight_value',
    COUNT(*)
FROM silver.order_items
WHERE freight_value < 0

UNION ALL

SELECT
    'negative_payment_value',
    COUNT(*)
FROM silver.payments
WHERE payment_value < 0;


-- ============================================================
-- 7. Overall quality summary
-- ============================================================

CREATE OR REPLACE TABLE quality.summary AS
SELECT
    'required_fields' AS check_group,
    COUNT(*) AS checks_run,
    SUM(CASE WHEN failed_rows > 0 THEN 1 ELSE 0 END) AS failed_checks
FROM quality.required_field_checks

UNION ALL

SELECT
    'duplicate_keys',
    COUNT(*),
    SUM(CASE WHEN duplicate_rows > 0 THEN 1 ELSE 0 END)
FROM quality.duplicate_key_checks

UNION ALL

SELECT
    'referential_integrity',
    COUNT(*),
    SUM(CASE WHEN orphan_rows > 0 THEN 1 ELSE 0 END)
FROM quality.referential_integrity_checks

UNION ALL

SELECT
    'chronology',
    COUNT(*),
    SUM(CASE WHEN failed_rows > 0 THEN 1 ELSE 0 END)
FROM quality.chronology_checks

UNION ALL

SELECT
    'monetary_values',
    COUNT(*),
    SUM(CASE WHEN failed_rows > 0 THEN 1 ELSE 0 END)
FROM quality.monetary_checks;
