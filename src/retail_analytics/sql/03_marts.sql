-- Reporting marts. Every mart is built from gold.fct_orders WHERE is_valid,
-- and every state-level mart is built with GROUPING SETS so a state's numbers
-- and the national numbers come from the same query. scope = 'ALL' or a state code.

CREATE OR REPLACE TABLE gold.mart_scope_kpis AS
WITH valid AS (
    SELECT o.*, d.customer_state
    FROM gold.fct_orders o
    JOIN gold.dim_customer d USING (customer_unique_id)
    WHERE o.is_valid
),
per_customer AS (
    SELECT customer_unique_id, customer_state, COUNT(*) AS orders
    FROM valid
    GROUP BY ALL
),
order_level AS (
    SELECT
        COALESCE(customer_state, 'ALL') AS scope,
        COUNT(*)                         AS orders,
        COUNT(DISTINCT customer_unique_id) AS customers,
        SUM(order_value)                 AS revenue,
        AVG(order_value)                 AS avg_order_value,
        AVG(review_score)                AS avg_review_score,
        AVG(is_late::INT) FILTER (WHERE is_late IS NOT NULL) AS late_delivery_rate,
        median(delivery_days)            AS median_delivery_days
    FROM valid
    GROUP BY GROUPING SETS ((), (customer_state))
),
repeat_level AS (
    SELECT
        COALESCE(customer_state, 'ALL') AS scope,
        AVG((orders >= 2)::INT) AS repeat_customer_rate
    FROM per_customer
    GROUP BY GROUPING SETS ((), (customer_state))
)
SELECT * FROM order_level JOIN repeat_level USING (scope);

CREATE OR REPLACE TABLE gold.mart_monthly_kpis AS
SELECT
    COALESCE(o.order_state, 'ALL') AS scope,
    o.order_month,
    m.is_partial,
    COUNT(*)                            AS orders,
    COUNT(DISTINCT o.customer_unique_id) AS customers,
    SUM(o.order_value)                  AS revenue,
    AVG(o.order_value)                  AS avg_order_value,
    AVG(o.review_score)                 AS avg_review_score,
    AVG(o.is_late::INT) FILTER (WHERE o.is_late IS NOT NULL) AS late_delivery_rate
FROM gold.fct_orders o
JOIN gold.dim_month m USING (order_month)
WHERE o.is_valid
GROUP BY GROUPING SETS ((o.order_month, m.is_partial), (o.order_state, o.order_month, m.is_partial));

CREATE OR REPLACE TABLE gold.mart_category_kpis AS
SELECT
    COALESCE(o.order_state, 'ALL') AS scope,
    p.category,
    COUNT(DISTINCT i.order_id)  AS orders,
    COUNT(*)                    AS items_sold,
    COUNT(DISTINCT i.product_id) AS products,
    SUM(i.price)                AS product_revenue,
    SUM(i.freight_value)        AS freight_revenue,
    SUM(i.line_value)           AS gmv,
    AVG(i.price)                AS avg_item_price,
    AVG(o.review_score)         AS avg_review_score
FROM gold.fct_order_items i
JOIN gold.fct_orders o USING (order_id)
JOIN gold.dim_product p USING (product_id)
WHERE o.is_valid
GROUP BY GROUPING SETS ((p.category), (o.order_state, p.category));

-- ---------------------------------------------------------------------------
-- RFM
-- About 97% of customers buy once, so a quintile on frequency would split
-- identical customers arbitrarily. Frequency is therefore used as a tier
-- (1 order vs repeat), and only recency and monetary value are quintiled,
-- with customer_unique_id as tie-breaker so every build gives the same answer.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE gold.mart_rfm AS
WITH reference AS (
    SELECT MAX(purchase_date) + 1 AS as_of FROM gold.fct_orders WHERE is_valid
),
customer AS (
    SELECT
        customer_unique_id,
        MAX(purchase_date)  AS last_purchase_date,
        MIN(purchase_date)  AS first_purchase_date,
        COUNT(*)            AS frequency,
        SUM(order_value)    AS monetary_value,
        AVG(review_score)   AS avg_review_score
    FROM gold.fct_orders
    WHERE is_valid AND order_value IS NOT NULL
    GROUP BY customer_unique_id
),
scored AS (
    SELECT
        c.*,
        date_diff('day', c.last_purchase_date, r.as_of) AS recency_days,
        r.as_of,
        NTILE(5) OVER (ORDER BY date_diff('day', c.last_purchase_date, r.as_of) DESC, c.customer_unique_id) AS r_score,
        NTILE(5) OVER (ORDER BY c.monetary_value, c.customer_unique_id) AS m_score
    FROM customer c
    CROSS JOIN reference r
)
SELECT
    s.*,
    d.customer_state,
    d.customer_city,
    CASE WHEN frequency >= 2 THEN 'Repeat' ELSE 'One-time' END AS frequency_tier,
    CASE
        WHEN frequency >= 2 AND r_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN frequency >= 2 AND r_score >= 3                  THEN 'Loyal'
        WHEN frequency >= 2                                   THEN 'At Risk'
        WHEN r_score >= 4 AND m_score >= 4                    THEN 'Promising'
        WHEN r_score >= 4                                     THEN 'New'
        WHEN r_score = 3                                      THEN 'Needs Attention'
        WHEN m_score >= 4                                     THEN 'Lost High-Value'
        ELSE 'Hibernating'
    END AS segment
FROM scored s
JOIN gold.dim_customer d USING (customer_unique_id);

CREATE OR REPLACE TABLE gold.mart_segment_summary AS
WITH grouped AS (
    SELECT
        COALESCE(customer_state, 'ALL') AS scope,
        segment,
        COUNT(*)              AS customers,
        SUM(monetary_value)   AS revenue,
        AVG(frequency)        AS avg_orders,
        AVG(monetary_value)   AS avg_customer_value,
        AVG(recency_days)     AS avg_recency_days,
        AVG(avg_review_score) AS avg_review_score
    FROM gold.mart_rfm
    GROUP BY GROUPING SETS ((segment), (customer_state, segment))
)
SELECT
    *,
    revenue / SUM(revenue) OVER (PARTITION BY scope)       AS revenue_share,
    customers / SUM(customers) OVER (PARTITION BY scope)   AS customer_share
FROM grouped;

-- ---------------------------------------------------------------------------
-- Cohort retention. A cell is only produced when the month is observable
-- (before the data ends); unobserved months are unknown, not zero.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE gold.mart_cohort_retention AS
WITH last_month AS (
    SELECT MAX(order_month) AS m FROM gold.dim_month WHERE NOT is_partial
),
activity AS (
    SELECT
        customer_unique_id,
        order_month,
        MIN(order_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM gold.fct_orders
    WHERE is_valid
),
sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_size
    FROM activity
    GROUP BY cohort_month
),
cells AS (
    SELECT
        cohort_month,
        date_diff('month', cohort_month, order_month) AS month_number,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM activity
    GROUP BY ALL
)
SELECT
    c.cohort_month,
    c.month_number,
    c.active_customers,
    s.cohort_size,
    c.active_customers / s.cohort_size AS retention_rate,
    s.cohort_size >= {min_cohort_size} AS is_reliable
FROM cells c
JOIN sizes s USING (cohort_month)
JOIN gold.dim_month dm ON dm.order_month = c.cohort_month
CROSS JOIN last_month l
WHERE NOT dm.is_partial
  AND c.cohort_month + to_months(c.month_number) <= l.m;

-- ---------------------------------------------------------------------------
-- Delivery timeliness vs review score (input to stats.py).
-- Excludes undelivered orders, orders without a review, and the 23 orders whose
-- carrier hand-off is recorded after customer delivery (bad timestamps).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE TABLE gold.delivery_review AS
SELECT
    order_id,
    customer_unique_id,
    order_state,
    CASE WHEN is_late THEN 'Late' ELSE 'On time' END AS delivery_group,
    delivery_delay_days,
    review_score
FROM gold.fct_orders
WHERE is_valid
  AND is_late IS NOT NULL
  AND review_score IS NOT NULL
  AND delivered_to_carrier_at IS NOT NULL
  AND delivered_to_carrier_at <= delivered_at;
