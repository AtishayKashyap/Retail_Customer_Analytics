-- Data-quality checks. severity 'error' fails the build (build.py raises);
-- severity 'warning' is a known property of the source data, reported but tolerated.

CREATE SCHEMA IF NOT EXISTS quality;

CREATE OR REPLACE TABLE quality.check_results AS
WITH checks(check_group, check_name, severity, failed_rows, description) AS (
    -- uniqueness ------------------------------------------------------------
    SELECT 'uniqueness', 'orders.order_id', 'error',
           COUNT(*) - COUNT(DISTINCT order_id), 'Order ids are unique'
    FROM silver.orders
    UNION ALL
    SELECT 'uniqueness', 'customers.customer_id', 'error',
           COUNT(*) - COUNT(DISTINCT customer_id), 'Customer ids are unique'
    FROM silver.customers
    UNION ALL
    SELECT 'uniqueness', 'products.product_id', 'error',
           COUNT(*) - COUNT(DISTINCT product_id), 'Product ids are unique'
    FROM silver.products
    UNION ALL
    SELECT 'uniqueness', 'sellers.seller_id', 'error',
           COUNT(*) - COUNT(DISTINCT seller_id), 'Seller ids are unique'
    FROM silver.sellers
    UNION ALL
    SELECT 'uniqueness', 'order_items.(order_id, order_item_id)', 'error',
           COUNT(*) - COUNT(DISTINCT (order_id, order_item_id)), 'Order lines are unique'
    FROM silver.order_items
    UNION ALL
    SELECT 'uniqueness', 'reviews.review_id', 'warning',
           COUNT(*) - COUNT(DISTINCT review_id), 'Olist reuses a review id across orders of one purchase'
    FROM silver.reviews

    -- completeness ------------------------------------------------------------
    UNION ALL
    SELECT 'completeness', 'orders required fields', 'error',
           COUNT(*) FILTER (WHERE order_id IS NULL OR customer_id IS NULL OR order_status IS NULL OR purchased_at IS NULL),
           'Every order has an id, customer, status and purchase time'
    FROM silver.orders
    UNION ALL
    SELECT 'completeness', 'customers.customer_unique_id', 'error',
           COUNT(*) FILTER (WHERE customer_unique_id IS NULL), 'Every customer row maps to a person'
    FROM silver.customers
    UNION ALL
    SELECT 'completeness', 'delivered orders have a delivery date', 'warning',
           COUNT(*) FILTER (WHERE order_status = 'delivered' AND delivered_at IS NULL),
           'Delivered status without a delivery timestamp'
    FROM silver.orders
    UNION ALL
    SELECT 'completeness', 'valid orders have line items', 'warning',
           COUNT(*) FILTER (WHERE is_valid AND item_count = 0),
           'Valid orders with no line items carry no revenue'
    FROM gold.fct_orders

    -- type conversion: a value that was present as text but failed to parse ---
    UNION ALL
    SELECT 'type_conversion', 'orders timestamps', 'error',
           COUNT(*) FILTER (WHERE (b.order_purchase_timestamp IS NOT NULL AND s.purchased_at IS NULL)
                               OR (b.order_delivered_customer_date IS NOT NULL AND s.delivered_at IS NULL)
                               OR (b.order_estimated_delivery_date IS NOT NULL AND s.estimated_delivery_date IS NULL)),
           'Order timestamps parse'
    FROM bronze.orders b JOIN silver.orders s USING (order_id)
    UNION ALL
    SELECT 'type_conversion', 'order_items money', 'error',
           COUNT(*) FILTER (WHERE (b.price IS NOT NULL AND s.price IS NULL)
                               OR (b.freight_value IS NOT NULL AND s.freight_value IS NULL)),
           'Prices and freight parse as decimals'
    FROM bronze.order_items b
    JOIN silver.order_items s ON s.order_id = b.order_id AND s.order_item_id = try_cast(b.order_item_id AS INTEGER)
    UNION ALL
    SELECT 'type_conversion', 'reviews.review_score', 'error',
           COUNT(*) FILTER (WHERE b.review_score IS NOT NULL AND try_cast(b.review_score AS INTEGER) IS NULL),
           'Review scores parse as integers'
    FROM bronze.reviews b

    -- referential integrity ---------------------------------------------------
    UNION ALL
    SELECT 'referential_integrity', 'orders -> customers', 'error', COUNT(*), 'Every order has a customer'
    FROM silver.orders o ANTI JOIN silver.customers c USING (customer_id)
    UNION ALL
    SELECT 'referential_integrity', 'order_items -> orders', 'error', COUNT(*), 'Every line belongs to an order'
    FROM silver.order_items i ANTI JOIN silver.orders o USING (order_id)
    UNION ALL
    SELECT 'referential_integrity', 'order_items -> products', 'error', COUNT(*), 'Every line has a product'
    FROM silver.order_items i ANTI JOIN silver.products p USING (product_id)
    UNION ALL
    SELECT 'referential_integrity', 'order_items -> sellers', 'error', COUNT(*), 'Every line has a seller'
    FROM silver.order_items i ANTI JOIN silver.sellers s USING (seller_id)
    UNION ALL
    SELECT 'referential_integrity', 'payments -> orders', 'error', COUNT(*), 'Every payment belongs to an order'
    FROM silver.payments p ANTI JOIN silver.orders o USING (order_id)
    UNION ALL
    SELECT 'referential_integrity', 'reviews -> orders', 'error', COUNT(*), 'Every review belongs to an order'
    FROM silver.reviews r ANTI JOIN silver.orders o USING (order_id)
    UNION ALL
    SELECT 'referential_integrity', 'products -> category translation', 'warning', COUNT(DISTINCT product_category_name),
           'Categories without an English name (shown in Portuguese)'
    FROM silver.products p ANTI JOIN silver.category_translation t USING (product_category_name)
    WHERE p.product_category_name IS NOT NULL

    -- validity -----------------------------------------------------------------
    UNION ALL
    SELECT 'validity', 'non-negative money', 'error',
           COUNT(*) FILTER (WHERE price < 0 OR freight_value < 0), 'Prices and freight are not negative'
    FROM silver.order_items
    UNION ALL
    SELECT 'validity', 'non-negative payments', 'error',
           COUNT(*) FILTER (WHERE payment_value < 0), 'Payments are not negative'
    FROM silver.payments
    UNION ALL
    SELECT 'validity', 'review score in 1..5', 'error',
           COUNT(*) FILTER (WHERE review_score NOT BETWEEN 1 AND 5), 'Review scores are on the 1-5 scale'
    FROM silver.reviews
    UNION ALL
    SELECT 'validity', 'known order status', 'error',
           COUNT(*) FILTER (WHERE order_status NOT IN
               ('created', 'approved', 'invoiced', 'processing', 'shipped', 'delivered', 'canceled', 'unavailable')),
           'Order status is one of the documented values'
    FROM silver.orders

    -- chronology -----------------------------------------------------------------
    UNION ALL
    SELECT 'chronology', 'delivered after purchase', 'error',
           COUNT(*) FILTER (WHERE delivered_at < purchased_at), 'Nothing is delivered before it is bought'
    FROM silver.orders
    UNION ALL
    SELECT 'chronology', 'approved after purchase', 'error',
           COUNT(*) FILTER (WHERE approved_at < purchased_at), 'Payment approval follows purchase'
    FROM silver.orders
    UNION ALL
    SELECT 'chronology', 'carrier hand-off before customer delivery', 'warning',
           COUNT(*) FILTER (WHERE delivered_to_carrier_at > delivered_at),
           'Source timestamps out of order; these orders are excluded from the delivery analysis'
    FROM silver.orders

    -- reconciliation ---------------------------------------------------------------
    UNION ALL
    SELECT 'reconciliation', 'payments = items + freight', 'warning',
           COUNT(*) FILTER (WHERE abs(payment_value - order_value) > 0.01),
           'Payment total differs from line total (vouchers, interest on instalments)'
    FROM gold.fct_orders
    WHERE payment_value IS NOT NULL AND order_value IS NOT NULL
)
SELECT
    *,
    failed_rows = 0 AS passed
FROM checks;
