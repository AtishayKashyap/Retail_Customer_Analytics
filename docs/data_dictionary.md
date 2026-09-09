# Data Dictionary

## Silver Layer

### silver.customers

| Column | Description |
|---|---|
| `customer_id` | Customer identifier used by the order system |
| `customer_unique_id` | Persistent customer identifier used for customer-level analysis |
| `customer_zip_code_prefix` | Customer postal-code prefix |
| `customer_city` | Customer city |
| `customer_state` | Customer state |

### silver.orders

| Column | Description |
|---|---|
| `order_id` | Unique order identifier |
| `customer_id` | Customer associated with the order |
| `order_status` | Order lifecycle status |
| `order_purchase_timestamp` | Purchase timestamp |
| `order_approved_at` | Payment approval timestamp |
| `order_delivered_carrier_date` | Carrier delivery timestamp |
| `order_delivered_customer_date` | Customer delivery timestamp |
| `order_estimated_delivery_date` | Estimated delivery timestamp |

### silver.order_items

| Column | Description |
|---|---|
| `order_id` | Order identifier |
| `order_item_id` | Item sequence within an order |
| `product_id` | Product identifier |
| `seller_id` | Seller identifier |
| `shipping_limit_date` | Seller shipping deadline |
| `price` | Product price |
| `freight_value` | Freight value |

### silver.products

| Column | Description |
|---|---|
| `product_id` | Product identifier |
| `product_category_name` | Original product category |
| `product_name_length` | Product name length |
| `product_description_length` | Product description length |
| `product_photos_qty` | Number of product photos |
| `product_weight_g` | Product weight |
| `product_length_cm` | Product length |
| `product_height_cm` | Product height |
| `product_width_cm` | Product width |

### silver.sellers

| Column | Description |
|---|---|
| `seller_id` | Seller identifier |
| `seller_zip_code_prefix` | Seller postal-code prefix |
| `seller_city` | Seller city |
| `seller_state` | Seller state |

### silver.payments

| Column | Description |
|---|---|
| `order_id` | Order identifier |
| `payment_sequential` | Payment sequence within an order |
| `payment_type` | Payment method |
| `payment_installments` | Number of installments |
| `payment_value` | Payment amount |

### silver.reviews

| Column | Description |
|---|---|
| `review_id` | Review identifier |
| `order_id` | Associated order |
| `review_score` | Customer review score |
| `review_creation_date` | Review creation timestamp |
| `review_answer_timestamp` | Review response timestamp |
| `review_comment_title` | Review title |
| `review_comment_message` | Review message |

## Gold Layer

### gold.customer_order_history

Order-level analytical view combining customer, order, item, and review information.

Key fields include:

- `order_id`
- `customer_unique_id`
- `order_status`
- `order_purchase_timestamp`
- `order_value`
- `item_count`
- `product_count`
- `review_score`

### gold.customer_360

Customer-level analytical mart.

Key metrics include:

- `first_order_date`
- `last_order_date`
- `order_count`
- `total_revenue`
- `avg_order_value`
- `total_items`
- `avg_review_score`
- `customer_state`
- `customer_city`

### gold.customer_rfm

Customer-level RFM inputs:

- `recency_days`
- `frequency`
- `monetary_value`
- `customer_type`

### gold.customer_segments

Customer-level RFM scoring and segment assignment.

Key fields:

- `recency_score`
- `frequency_score`
- `monetary_score`
- `rfm_score`
- `segment`

### gold.cohort_retention

Cohort retention analysis containing:

- `cohort_month`
- `order_month`
- `month_number`
- `active_customers`
- `cohort_size`
- `retention_rate_pct`

### gold.monthly_kpis

Overall monthly performance metrics.

### gold.state_monthly_kpis

Monthly performance metrics grouped by customer state.

### gold.category_kpis

Overall product-category performance metrics.

### gold.state_category_kpis

Product-category performance grouped by customer state.

### gold.segment_summary

Overall customer-segment business summary containing:

- Customer count
- Segment revenue
- Revenue share
- Average orders
- Average customer value
- Average recency

### gold.state_segment_summary

Customer-segment business metrics grouped by customer state.

### gold.business_insights

Structured analytical findings containing:

- `insight_type`
- `priority`
- `headline`
- `detail`
- `metric_value`
- `metric_label`
- `recommended_action`
