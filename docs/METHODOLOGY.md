# Methodology

## Definitions

| Term | Definition |
|---|---|
| Valid order | `order_status` not in (`canceled`, `unavailable`). Used by every KPI, segment and cohort. |
| Revenue / order value | Sum of item price + freight over the order's lines (`fct_order_items`). Payment totals differ for 366 orders (vouchers, instalment interest) and are reported as a reconciliation warning. |
| Customer | `customer_unique_id`. Olist issues a new `customer_id` per order. |
| Customer location | State and city of the customer's most recent order (39 people changed state). |
| Late | Delivered on a later calendar day than `order_estimated_delivery_date`. NULL when not delivered. |
| Partial month | A month with fewer than 10% of the median monthly orders: 2016-09, 2016-10, 2016-12, 2018-09, 2018-10. Excluded from trends and cohorts. |
| Review score | Mean of the order's reviews (a few orders have more than one). |

## RFM segments

- **Reference date:** the day after the last valid purchase in the data.
- **R (recency)** and **M (monetary)** are quintiles 1-5 (5 = most recent, highest spend), computed with `NTILE(5)`
  and `customer_unique_id` as tie-breaker so the assignment is identical on every build.
- **F (frequency)** is a tier: one order or repeat (2+). A quintile is meaningless when 97% of customers share the
  value 1: `NTILE` would place identical customers in different scores by row order.

Rules are applied top to bottom; the first match wins.

| Segment | Rule | Suggested action |
|---|---|---|
| Champions | repeat, R >= 4, M >= 4 | Protect: early access, loyalty benefits |
| Loyal | repeat, R >= 3 | Grow basket size with recommendations |
| At Risk | repeat, R <= 2 | Win back before they lapse for good |
| Promising | one order, R >= 4, M >= 4 | Second-order incentive while the first is recent |
| New | one order, R >= 4 | Onboarding and follow-up offers |
| Needs Attention | one order, R = 3 | Re-engage with category-relevant offers |
| Lost High-Value | one order, R <= 2, M >= 4 | Targeted win-back on the category they bought |
| Hibernating | one order, R <= 2, M <= 3 | Low-cost reactivation only |

## Cohort retention

Cohort = month of a customer's first valid order. A cell is the share of the cohort with a valid order N months
later. Cells after the last complete month are not produced (they are unknown, not zero), cohorts in partial months
are dropped, and cohorts under 30 customers are flagged `is_reliable = false` and hidden in the dashboard.

## Delivery timeliness vs review score

**Question.** Do customers whose order arrives late rate it differently?

**Sample.** Valid, delivered orders with a review, excluding the 23 orders whose carrier hand-off is recorded after
customer delivery: 89,420 on time and 6,380 late.

**Method.**
- Two-sided Mann-Whitney U test on order-level scores. It tests whether one group tends to score higher
  (stochastic dominance), which suits a 1-5 ordinal scale; it is not a test of medians.
- Effect size: rank-biserial correlation r = P(on-time > late) - P(on-time < late), with a 2,000-resample percentile
  bootstrap interval.
- Share of 1-2 star reviews per group with Wilson intervals, and Newcombe's interval for the difference.
- The interpretation sentence is generated from the result; if the test were not significant it would say so.

**Result.** r = 0.64 (95% CI 0.63 to 0.65), a large effect; 62.4% of late orders get 1-2 stars against 9.2% of
on-time orders, a difference of 53.1 percentage points (95% CI 51.9 to 54.3). p is below double-precision range,
reported as p < 1e-300.

**Limitations.**
- Observational: late orders also differ by region, category, seller and freight cost. This is association, not a
  causal estimate.
- Olist sends its satisfaction survey around the promised delivery date, so some late-order reviews were written
  before the parcel arrived; part of the effect is "it hasn't come yet".
- Orders are not fully independent (repeat customers, shared sellers). At this sample size that does not change the
  conclusion, but the intervals are somewhat narrower than they should be.
