CREATE SCHEMA IF NOT EXISTS gold;

-- ============================================================
-- 1. Customer-level order history
-- ============================================================

CREATE OR REPLACE TABLE gold.customer_order_history AS
SELECT
    o.order_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    SUM(oi.price) AS item_revenue,
    SUM(oi.freight_value) AS freight_revenue,
    SUM(oi.price + oi.freight_value) AS order_value,
    COUNT(DISTINCT oi.order_item_id) AS item_count,
    COUNT(DISTINCT oi.product_id) AS product_count,
    rs.avg_review_score AS review_score
FROM silver.orders o
JOIN silver.customers c
    ON o.customer_id = c.customer_id
LEFT JOIN silver.order_items oi
    ON o.order_id = oi.order_id
LEFT JOIN silver.order_review_summary rs
    ON o.order_id = rs.order_id
GROUP BY
    o.order_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    rs.avg_review_score;


-- ============================================================
-- 2. Customer 360
-- ============================================================

CREATE OR REPLACE TABLE gold.customer_360 AS
SELECT
    customer_unique_id,
    MIN(order_purchase_timestamp) AS first_order_date,
    MAX(order_purchase_timestamp) AS last_order_date,
    COUNT(DISTINCT order_id) AS order_count,

    SUM(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
            ELSE 0
        END
    ) AS total_revenue,

    AVG(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
        END
    ) AS avg_order_value,

    SUM(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN item_count
            ELSE 0
        END
    ) AS total_items,

    AVG(review_score) AS avg_review_score,
    MAX(customer_state) AS customer_state,
    MAX(customer_city) AS customer_city

FROM gold.customer_order_history
GROUP BY customer_unique_id;


-- ============================================================
-- 3. Monthly KPI mart
-- ============================================================

CREATE OR REPLACE TABLE gold.monthly_kpis AS
SELECT
    DATE_TRUNC('month', order_purchase_timestamp) AS order_month,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(DISTINCT customer_unique_id) AS unique_customers,

    SUM(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
            ELSE 0
        END
    ) AS revenue,

    AVG(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
        END
    ) AS avg_order_value,

    AVG(review_score) AS avg_review_score

FROM gold.customer_order_history
GROUP BY 1
ORDER BY 1;


-- ============================================================
-- 4. State x Month KPI mart
-- ============================================================

CREATE OR REPLACE TABLE gold.state_monthly_kpis AS
SELECT
    c.customer_state,
    DATE_TRUNC('month', o.order_purchase_timestamp) AS order_month,

    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT c.customer_unique_id) AS unique_customers,

    SUM(
        CASE
            WHEN o.order_status NOT IN ('canceled', 'unavailable')
            THEN COALESCE(v.order_value, 0)
            ELSE 0
        END
    ) AS revenue,

    AVG(
        CASE
            WHEN o.order_status NOT IN ('canceled', 'unavailable')
            THEN v.order_value
        END
    ) AS avg_order_value

FROM silver.orders o
JOIN silver.customers c
    ON o.customer_id = c.customer_id
LEFT JOIN (
    SELECT
        order_id,
        SUM(price + freight_value) AS order_value
    FROM silver.order_items
    GROUP BY order_id
) v
    ON o.order_id = v.order_id

GROUP BY
    c.customer_state,
    DATE_TRUNC('month', o.order_purchase_timestamp)

ORDER BY
    c.customer_state,
    order_month;


-- ============================================================
-- 5. Category KPI mart
-- ============================================================

CREATE OR REPLACE TABLE gold.category_kpis AS
SELECT
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    ) AS category,

    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(DISTINCT oi.product_id) AS unique_products,
    COUNT(*) AS items_sold,

    SUM(oi.price) AS product_revenue,
    SUM(oi.freight_value) AS freight_revenue,
    SUM(oi.price + oi.freight_value) AS gross_merchandise_value,
    AVG(oi.price) AS avg_item_price

FROM silver.order_items oi
LEFT JOIN silver.products p
    ON oi.product_id = p.product_id
LEFT JOIN silver.category_translation ct
    ON p.product_category_name = ct.product_category_name

GROUP BY 1
ORDER BY gross_merchandise_value DESC;


-- ============================================================
-- 6. State x Category KPI mart
-- ============================================================

CREATE OR REPLACE TABLE gold.state_category_kpis AS
SELECT
    c.customer_state,

    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    ) AS category,

    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(DISTINCT oi.product_id) AS unique_products,
    COUNT(*) AS items_sold,

    SUM(oi.price) AS product_revenue,
    SUM(oi.freight_value) AS freight_revenue,
    SUM(oi.price + oi.freight_value) AS gross_merchandise_value,
    AVG(oi.price) AS avg_item_price

FROM silver.order_items oi
JOIN silver.orders o
    ON oi.order_id = o.order_id
JOIN silver.customers c
    ON o.customer_id = c.customer_id
LEFT JOIN silver.products p
    ON oi.product_id = p.product_id
LEFT JOIN silver.category_translation ct
    ON p.product_category_name = ct.product_category_name

WHERE o.order_status NOT IN ('canceled', 'unavailable')

GROUP BY
    c.customer_state,
    COALESCE(
        ct.product_category_name_english,
        p.product_category_name,
        'unknown'
    )

ORDER BY
    c.customer_state,
    gross_merchandise_value DESC;


-- ============================================================
-- 7. Cohort retention
-- ============================================================

CREATE OR REPLACE TABLE gold.cohort_retention AS
WITH customer_orders AS (
    SELECT
        customer_unique_id,

        DATE_TRUNC(
            'month',
            MIN(order_purchase_timestamp)
                OVER (PARTITION BY customer_unique_id)
        ) AS cohort_month,

        DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS order_month

    FROM gold.customer_order_history

    WHERE order_status NOT IN ('canceled', 'unavailable')
),

cohort_activity AS (
    SELECT
        cohort_month,
        order_month,

        DATE_DIFF(
            'month',
            cohort_month,
            order_month
        ) AS month_number,

        COUNT(DISTINCT customer_unique_id) AS active_customers

    FROM customer_orders

    GROUP BY
        cohort_month,
        order_month
),

cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_unique_id) AS cohort_size

    FROM customer_orders

    GROUP BY cohort_month
)

SELECT
    ca.cohort_month,
    ca.order_month,
    ca.month_number,
    ca.active_customers,
    cs.cohort_size,

    ROUND(
        100.0 * ca.active_customers
        / NULLIF(cs.cohort_size, 0),
        2
    ) AS retention_rate_pct

FROM cohort_activity ca
JOIN cohort_sizes cs
    ON ca.cohort_month = cs.cohort_month

ORDER BY
    ca.cohort_month,
    ca.month_number;


-- ============================================================
-- 8. RFM-ready customer metrics
-- ============================================================

CREATE OR REPLACE TABLE gold.customer_rfm AS
WITH reference_date AS (
    SELECT MAX(last_order_date) AS max_order_date
    FROM gold.customer_360
)

SELECT
    c.customer_unique_id,

    DATE_DIFF(
        'day',
        c.last_order_date,
        r.max_order_date
    ) AS recency_days,

    c.order_count AS frequency,
    c.total_revenue AS monetary_value,

    CASE
        WHEN c.order_count = 1 THEN 'One-time'
        WHEN c.order_count BETWEEN 2 AND 3 THEN 'Repeat'
        WHEN c.order_count >= 4 THEN 'Loyal'
        ELSE 'Unknown'
    END AS customer_type

FROM gold.customer_360 c
CROSS JOIN reference_date r;


-- ============================================================
-- 9. RFM customer segments
-- ============================================================

CREATE OR REPLACE TABLE gold.customer_segments AS
WITH scored AS (
    SELECT
        *,

        NTILE(5) OVER (
            ORDER BY recency_days DESC
        ) AS recency_score,

        NTILE(5) OVER (
            ORDER BY frequency
        ) AS frequency_score,

        NTILE(5) OVER (
            ORDER BY monetary_value
        ) AS monetary_score

    FROM gold.customer_rfm
)

SELECT
    *,

    recency_score
        + frequency_score
        + monetary_score AS rfm_score,

    CASE
        WHEN recency_score >= 4
         AND frequency_score >= 4
         AND monetary_score >= 4
            THEN 'Champions'

        WHEN recency_score >= 4
         AND frequency_score >= 3
            THEN 'Loyal Customers'

        WHEN recency_score >= 4
         AND monetary_score >= 3
            THEN 'Potential Loyalists'

        WHEN recency_score <= 2
         AND frequency_score >= 3
            THEN 'At Risk'

        WHEN recency_score <= 2
         AND frequency_score <= 2
            THEN 'Hibernating'

        ELSE 'Needs Attention'
    END AS segment

FROM scored;


-- ============================================================
-- 10. Segment-level business summary
-- ============================================================

CREATE OR REPLACE TABLE gold.segment_summary AS
WITH totals AS (
    SELECT
        SUM(total_revenue) AS total_revenue
    FROM gold.customer_360
)

SELECT
    cs.segment,
    COUNT(*) AS customers,
    SUM(cs.monetary_value) AS segment_revenue,

    ROUND(
        100.0 * SUM(cs.monetary_value)
        / NULLIF(t.total_revenue, 0),
        2
    ) AS revenue_share_pct,

    ROUND(
        AVG(cs.frequency),
        2
    ) AS avg_orders,

    ROUND(
        AVG(cs.monetary_value),
        2
    ) AS avg_customer_value,

    ROUND(
        AVG(cs.recency_days),
        1
    ) AS avg_recency_days

FROM gold.customer_segments cs
CROSS JOIN totals t

GROUP BY
    cs.segment,
    t.total_revenue

ORDER BY
    segment_revenue DESC;

-- ============================================================
-- 11. State x Segment business summary
-- ============================================================

CREATE OR REPLACE TABLE gold.state_segment_summary AS
WITH state_totals AS (
    SELECT
        customer_state,
        SUM(total_revenue) AS state_revenue
    FROM gold.customer_360
    GROUP BY customer_state
)

SELECT
    c.customer_state,
    cs.segment,

    COUNT(*) AS customers,

    SUM(cs.monetary_value) AS segment_revenue,

    ROUND(
        100.0 * SUM(cs.monetary_value)
        / NULLIF(st.state_revenue, 0),
        2
    ) AS revenue_share_pct,

    ROUND(AVG(cs.frequency), 2) AS avg_orders,

    ROUND(AVG(cs.monetary_value), 2) AS avg_customer_value,

    ROUND(AVG(cs.recency_days), 1) AS avg_recency_days

FROM gold.customer_segments cs

JOIN gold.customer_360 c
    ON cs.customer_unique_id = c.customer_unique_id

JOIN state_totals st
    ON c.customer_state = st.customer_state

GROUP BY
    c.customer_state,
    cs.segment,
    st.state_revenue

ORDER BY
    c.customer_state,
    segment_revenue DESC;


-- ============================================================
-- 12. Automated business insights
-- ============================================================

CREATE OR REPLACE TABLE gold.business_insights AS

WITH overall AS (
    SELECT
        SUM(total_revenue) AS total_revenue,
        COUNT(*) AS total_customers,
        SUM(
            CASE
                WHEN order_count >= 2 THEN 1
                ELSE 0
            END
        ) AS repeat_customers
    FROM gold.customer_360
),

top_segment AS (
    SELECT
        segment,
        customers,
        segment_revenue,
        revenue_share_pct,
        avg_customer_value
    FROM gold.segment_summary
    ORDER BY segment_revenue DESC
    LIMIT 1
),

at_risk AS (
    SELECT
        segment,
        customers,
        segment_revenue,
        revenue_share_pct,
        avg_customer_value
    FROM gold.segment_summary
    WHERE segment = 'At Risk'
    LIMIT 1
),

top_category AS (
    SELECT
        category,
        gross_merchandise_value,
        total_orders,
        items_sold
    FROM gold.category_kpis
    ORDER BY gross_merchandise_value DESC
    LIMIT 1
),

top_state AS (
    SELECT
        customer_state,
        SUM(revenue) AS revenue
    FROM gold.state_monthly_kpis
    GROUP BY customer_state
    ORDER BY revenue DESC
    LIMIT 1
)

SELECT
    'segment' AS insight_type,
    'high' AS priority,
    'Highest-value customer segment' AS headline,
    CONCAT(
        top_segment.segment,
        ' contributes ',
        CAST(ROUND(top_segment.revenue_share_pct, 1) AS VARCHAR),
        '% of customer revenue with ',
        CAST(top_segment.customers AS VARCHAR),
        ' customers.'
    ) AS detail,
    top_segment.segment_revenue AS metric_value,
    'Segment revenue' AS metric_label,
    'Protect and expand this segment through retention and cross-sell activity.'
        AS recommended_action
FROM top_segment

UNION ALL

SELECT
    'risk',
    'high',
    'Revenue currently exposed to At Risk customers',
    CONCAT(
        CAST(at_risk.customers AS VARCHAR),
        ' customers are classified as At Risk and represent ',
        CAST(ROUND(at_risk.revenue_share_pct, 1) AS VARCHAR),
        '% of customer revenue.'
    ),
    at_risk.segment_revenue,
    'At Risk revenue',
    'Prioritize win-back campaigns and investigate recent purchase declines.'
FROM at_risk

UNION ALL

SELECT
    'category',
    'medium',
    'Strongest product category',
    CONCAT(
        top_category.category,
        ' leads categories with ',
        CAST(top_category.total_orders AS VARCHAR),
        ' orders.'
    ),
    top_category.gross_merchandise_value,
    'Category GMV',
    'Evaluate inventory, pricing, and cross-sell opportunities around this category.'
FROM top_category

UNION ALL

SELECT
    'geography',
    'medium',
    'Highest-revenue customer state',
    CONCAT(
        top_state.customer_state,
        ' generates the largest aggregate customer revenue.'
    ),
    top_state.revenue,
    'State revenue',
    'Use the leading market as a benchmark when evaluating lower-performing regions.'
FROM top_state

UNION ALL

SELECT
    'retention',
    'medium',
    'Repeat-customer share',
    CONCAT(
        CAST(ROUND(
            100.0 * overall.repeat_customers
            / NULLIF(overall.total_customers, 0),
            1
        ) AS VARCHAR),
        '% of customers have placed at least two orders.'
    ),
    100.0 * overall.repeat_customers
        / NULLIF(overall.total_customers, 0),
    'Repeat customer %',
    'Focus retention efforts on converting one-time buyers into repeat customers.'
FROM overall

UNION ALL

SELECT
    'concentration',
    'medium',
    'Top segment revenue concentration',
    CONCAT(
        'The largest customer segment accounts for ',
        CAST(ROUND(top_segment.revenue_share_pct, 1) AS VARCHAR),
        '% of total customer revenue.'
    ),
    top_segment.revenue_share_pct,
    'Revenue share %',
    'Balance retention investment with acquisition and development of secondary segments.'
FROM top_segment;

