# Data model

All tables live in one DuckDB file. Schemas: `bronze` (raw text), `silver` (typed), `gold` (star schema and marts),
`quality` (check results).

## Star schema

| Table | Grain | Key columns |
|---|---|---|
| `gold.fct_orders` | one row per order | `order_id`, `customer_unique_id`, `order_state`, `order_status`, `is_valid`, `purchased_at`, `order_month`, `delivered_at`, `estimated_delivery_date`, `is_late`, `delivery_delay_days`, `delivery_days`, `item_revenue`, `freight_revenue`, `order_value`, `payment_value`, `item_count`, `review_score` |
| `gold.fct_order_items` | one row per order line | `order_id`, `order_item_id`, `product_id`, `seller_id`, `price`, `freight_value`, `line_value` |
| `gold.dim_customer` | one row per person | `customer_unique_id`, `customer_state`, `customer_city` |
| `gold.dim_product` | one row per product | `product_id`, `category` (English, falls back to Portuguese), `is_translated` |
| `gold.dim_seller` | one row per seller | `seller_id`, `seller_state`, `seller_city` |
| `gold.dim_date` | one row per calendar day | `date`, `month`, `year`, `quarter`, `day_of_week` |
| `gold.dim_month` | one row per month with orders | `order_month`, `orders`, `is_partial` |

## Marts

`scope` is `'ALL'` or a two-letter state code. National and state rows are produced by the same `GROUPING SETS`
query.

| Table | Grain | Used by |
|---|---|---|
| `gold.mart_scope_kpis` | scope | Overview metrics |
| `gold.mart_monthly_kpis` | scope x month | Monthly trend |
| `gold.mart_category_kpis` | scope x category | Categories tab |
| `gold.mart_rfm` | customer | Segments, customer lookup |
| `gold.mart_segment_summary` | scope x segment | Segments tab, insights |
| `gold.mart_cohort_retention` | cohort month x months since first purchase | Retention tab |
| `gold.delivery_review` | order | Statistical test |
| `quality.check_results` | check | Quality gate, Data Quality tab |
