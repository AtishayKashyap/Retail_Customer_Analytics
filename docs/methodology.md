# Analytical Methodology

## Revenue Definition

Revenue-oriented customer metrics exclude orders with status:

- `canceled`
- `unavailable`

Order value is calculated as:

    product price + freight value

## Customer Definition

Customer-level analysis uses `customer_unique_id` so repeat orders associated with the same underlying customer can be analyzed together.

## RFM Analysis

RFM analysis uses three behavioral dimensions.

### Recency

Number of days between a customer's last purchase and the latest purchase date represented in the analytical dataset.

### Frequency

Number of orders associated with the customer.

### Monetary Value

Total customer revenue under the project's revenue definition.

Customers are scored into five quantile groups using `NTILE(5)`.

The resulting scores are combined into behavioral segments:

- Champions
- Loyal Customers
- Potential Loyalists
- At Risk
- Hibernating
- Needs Attention

## Cohort Analysis

A customer's cohort is the calendar month of their first qualifying purchase.

Subsequent activity is tracked by the number of months elapsed since that first purchase.

Retention rate is calculated as active customers in a cohort month divided by the original cohort size.

## Data Quality

The quality layer checks:

- Required fields
- Duplicate keys
- Referential integrity
- Timestamp chronology
- Negative monetary values
- Expected analytical tables

The project surfaces source-data anomalies rather than silently modifying source records.

## Performance Benchmark

The benchmark compares the same customer-level analytical metrics using two approaches:

### Raw workload

Source-grain joins and aggregation across:

- `silver.customers`
- `silver.orders`
- `silver.order_items`

### Materialized workload

Reading equivalent metrics from:

- `gold.customer_360`

Five timed executions are performed for each workload following a warm-up execution.

The benchmark validates metric equivalence before reporting the performance difference.

The current observed median result is:

- Raw workload: 326.10 ms
- Materialized customer mart: 207.63 ms
- Median speedup: 1.57x

This result is workload-specific and depends on the dataset size, hardware, DuckDB version, and execution environment.
