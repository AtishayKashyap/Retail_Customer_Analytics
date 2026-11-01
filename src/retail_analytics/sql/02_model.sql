-- Star schema. One row per order in fct_orders, one per order line in fct_order_items.
-- "Valid" order = not canceled/unavailable. It is the single definition every mart uses.

CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE TABLE gold.dim_product AS
SELECT
    p.product_id,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category,
    p.product_category_name AS category_pt,
    t.product_category_name_english IS NOT NULL AS is_translated,
    p.product_weight_g,
    p.product_photos_qty
FROM silver.products p
LEFT JOIN silver.category_translation t USING (product_category_name);

CREATE OR REPLACE TABLE gold.dim_seller AS
SELECT seller_id, seller_city, seller_state, seller_zip_code_prefix
FROM silver.sellers;

-- Olist issues a new customer_id per order; customer_unique_id is the person.
-- Location = where their most recent order was shipped (39 people moved state).
CREATE OR REPLACE TABLE gold.dim_customer AS
SELECT
    c.customer_unique_id,
    arg_max(c.customer_state, o.purchased_at) AS customer_state,
    arg_max(c.customer_city, o.purchased_at)  AS customer_city
FROM silver.customers c
JOIN silver.orders o USING (customer_id)
GROUP BY c.customer_unique_id;

CREATE OR REPLACE TABLE gold.dim_date AS
SELECT
    d::DATE                       AS date,
    date_trunc('month', d)::DATE  AS month,
    year(d)                       AS year,
    quarter(d)                    AS quarter,
    dayofweek(d)                  AS day_of_week
FROM range(
    (SELECT min(purchased_at)::DATE FROM silver.orders),
    (SELECT max(GREATEST(purchased_at, delivered_at))::DATE + 1 FROM silver.orders),
    INTERVAL 1 DAY
) AS t(d);

CREATE OR REPLACE TABLE gold.fct_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.price,
    i.freight_value,
    i.price + i.freight_value AS line_value
FROM silver.order_items i;

CREATE OR REPLACE TABLE gold.fct_orders AS
WITH items AS (
    SELECT
        order_id,
        SUM(price)          AS item_revenue,
        SUM(freight_value)  AS freight_revenue,
        SUM(line_value)     AS order_value,
        COUNT(*)            AS item_count,
        COUNT(DISTINCT product_id) AS product_count
    FROM gold.fct_order_items
    GROUP BY order_id
),
payments AS (
    SELECT order_id, SUM(payment_value) AS payment_value
    FROM silver.payments
    GROUP BY order_id
),
reviews AS (
    -- A few orders carry several reviews; their scores are averaged.
    SELECT order_id, AVG(review_score) AS review_score, COUNT(*) AS review_count
    FROM silver.reviews
    GROUP BY order_id
)
SELECT
    o.order_id,
    c.customer_unique_id,
    c.customer_state AS order_state,
    o.order_status,
    o.order_status NOT IN ('canceled', 'unavailable') AS is_valid,
    o.purchased_at,
    o.purchased_at::DATE                       AS purchase_date,
    date_trunc('month', o.purchased_at)::DATE  AS order_month,
    o.delivered_to_carrier_at,
    o.delivered_at,
    o.estimated_delivery_date,
    -- Compared as dates: a parcel delivered at 15:00 on the promised day is on time.
    CASE WHEN o.delivered_at IS NULL OR o.estimated_delivery_date IS NULL THEN NULL
         ELSE o.delivered_at::DATE > o.estimated_delivery_date END AS is_late,
    date_diff('day', o.estimated_delivery_date, o.delivered_at::DATE) AS delivery_delay_days,
    date_diff('day', o.purchased_at::DATE, o.delivered_at::DATE)      AS delivery_days,
    i.item_revenue,
    i.freight_revenue,
    i.order_value,
    COALESCE(i.item_count, 0) AS item_count,
    COALESCE(i.product_count, 0) AS product_count,
    p.payment_value,
    r.review_score,
    COALESCE(r.review_count, 0) AS review_count
FROM silver.orders o
JOIN silver.customers c USING (customer_id)
LEFT JOIN items i USING (order_id)
LEFT JOIN payments p USING (order_id)
LEFT JOIN reviews r USING (order_id);

-- Months with too few orders to trend (the 2016 launch months and the cut-off tail in late 2018).
CREATE OR REPLACE TABLE gold.dim_month AS
WITH monthly AS (
    SELECT order_month, COUNT(*) AS orders
    FROM gold.fct_orders
    GROUP BY order_month
)
SELECT
    order_month,
    orders,
    orders < {partial_month_threshold} * (SELECT median(orders) FROM monthly) AS is_partial
FROM monthly;
