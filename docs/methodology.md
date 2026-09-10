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

## Hypothesis-Driven Statistical Analysis

### Question

Is delivery timeliness associated with customer review scores?

### Hypotheses

**Null hypothesis (H₀):** Review-score distributions do not differ between on-time and late deliveries.

**Alternative hypothesis (H₁):** Review-score distributions differ between on-time and late deliveries.

### Study design

This is an **observational analysis**, not a randomized experiment. Orders were classified using the recorded customer delivery date and estimated delivery date.

Orders with invalid delivery chronology were excluded from this statistical analysis while remaining preserved in the underlying analytical warehouse for auditability.

### Statistical method

A two-sided **Mann–Whitney U test** was used to compare review-score distributions between on-time and late deliveries. This non-parametric test was selected because review scores are discrete ordinal ratings on a 1–5 scale.

The significance threshold was:

`α = 0.05`

Effect magnitude was reported using the **rank-biserial correlation**.

A bootstrap procedure with 5,000 iterations and a fixed random seed was also used to quantify uncertainty around the difference in median review scores.

### Observed results

The analysis included:

- 88,140 on-time orders
- 7,660 late orders
- On-time mean review score: 4.295
- Late mean review score: 2.566
- On-time median review score: 5.0
- Late median review score: 2.0
- Mann–Whitney U statistic: 524,613,062
- p-value: below 0.001 at the reported precision
- Rank-biserial effect size: 0.554
- Median review-score difference: 3.0 points
- Bootstrap 95% CI for median difference: [3.0, 3.0]

### Interpretation

The analysis provides strong statistical evidence that review-score distributions differ between on-time and late deliveries. The observed difference is also substantial in magnitude, not merely statistically significant.

The result should be interpreted as an **association**, not a causal effect. Other factors may influence customer review scores, and the observational design does not establish that delivery lateness itself caused the difference.

### Reproducibility

The analysis is implemented in:

`scripts/statistical_analysis.py`

and the reproducible result artifact is written to:

`artifacts/statistical_analysis.json`

The bootstrap uses a fixed random seed of 42 so that the reported interval can be reproduced.
