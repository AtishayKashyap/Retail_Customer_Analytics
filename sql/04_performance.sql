CREATE SCHEMA IF NOT EXISTS performance;

-- ============================================================
-- 1. Add indexes to frequently filtered / joined Gold columns
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_customer_360_customer
ON gold.customer_360(customer_unique_id);

CREATE INDEX IF NOT EXISTS idx_customer_360_state
ON gold.customer_360(customer_state);

CREATE INDEX IF NOT EXISTS idx_customer_history_customer
ON gold.customer_order_history(customer_unique_id);

CREATE INDEX IF NOT EXISTS idx_customer_history_order_date
ON gold.customer_order_history(order_purchase_timestamp);

CREATE INDEX IF NOT EXISTS idx_monthly_kpis_month
ON gold.monthly_kpis(order_month);

CREATE INDEX IF NOT EXISTS idx_category_kpis_category
ON gold.category_kpis(category);

CREATE INDEX IF NOT EXISTS idx_cohort_retention_cohort
ON gold.cohort_retention(cohort_month);

CREATE INDEX IF NOT EXISTS idx_customer_segments_segment
ON gold.customer_segments(segment);


-- ============================================================
-- 2. Refresh table statistics
-- ============================================================

ANALYZE gold.customer_360;
ANALYZE gold.customer_order_history;
ANALYZE gold.monthly_kpis;
ANALYZE gold.category_kpis;
ANALYZE gold.cohort_retention;
ANALYZE gold.customer_segments;


-- ============================================================
-- 3. Warehouse performance metadata
-- ============================================================

CREATE OR REPLACE TABLE performance.table_stats AS
SELECT
    'gold.customer_360' AS table_name,
    COUNT(*) AS row_count
FROM gold.customer_360

UNION ALL

SELECT
    'gold.customer_order_history',
    COUNT(*)
FROM gold.customer_order_history

UNION ALL

SELECT
    'gold.monthly_kpis',
    COUNT(*)
FROM gold.monthly_kpis

UNION ALL

SELECT
    'gold.category_kpis',
    COUNT(*)
FROM gold.category_kpis

UNION ALL

SELECT
    'gold.cohort_retention',
    COUNT(*)
FROM gold.cohort_retention

UNION ALL

SELECT
    'gold.customer_segments',
    COUNT(*)
FROM gold.customer_segments;


-- ============================================================
-- 4. Record the intended performance methodology
-- ============================================================

CREATE OR REPLACE TABLE performance.benchmark_config AS
SELECT
    'raw_customer_aggregation' AS workload_name,
    'Join source-grain customer, order, and order-item data' AS workload_description

UNION ALL

SELECT
    'optimized_customer_mart',
    'Read equivalent metrics from gold.customer_360';

