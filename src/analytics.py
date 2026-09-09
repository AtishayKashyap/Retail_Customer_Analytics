from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH
from src.db import connect, query_df


def get_executive_kpis() -> pd.DataFrame:
    sql = """
    SELECT
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_unique_id) AS unique_customers,
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
        AVG(review_score) AS avg_review_score
    FROM gold.customer_order_history
    """
    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql)
    finally:
        con.close()


def get_monthly_kpis(state: str | None = None) -> pd.DataFrame:
    if state is None or state == "All":
        sql = """
        SELECT
            order_month,
            total_orders,
            unique_customers,
            revenue,
            avg_order_value,
            avg_review_score
        FROM gold.monthly_kpis
        ORDER BY order_month
        """
        params = ()
    else:
        sql = """
        SELECT
            order_month,
            total_orders,
            unique_customers,
            revenue,
            avg_order_value,
            NULL AS avg_review_score
        FROM gold.state_monthly_kpis
        WHERE customer_state = ?
        ORDER BY order_month
        """
        params = (state,)

    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql, params)
    finally:
        con.close()


def get_customer_segments(state: str | None = None) -> pd.DataFrame:
    if state is None or state == "All":
        sql = """
        SELECT
            segment,
            COUNT(*) AS customers,
            ROUND(AVG(monetary_value), 2) AS avg_customer_value,
            ROUND(AVG(frequency), 2) AS avg_orders,
            ROUND(AVG(recency_days), 1) AS avg_recency_days
        FROM gold.customer_segments
        GROUP BY segment
        ORDER BY customers DESC
        """
        params = ()
    else:
        sql = """
        SELECT
            cs.segment,
            COUNT(*) AS customers,
            ROUND(AVG(cs.monetary_value), 2) AS avg_customer_value,
            ROUND(AVG(cs.frequency), 2) AS avg_orders,
            ROUND(AVG(cs.recency_days), 1) AS avg_recency_days
        FROM gold.customer_segments cs
        JOIN gold.customer_360 c
            ON cs.customer_unique_id = c.customer_unique_id
        WHERE c.customer_state = ?
        GROUP BY cs.segment
        ORDER BY customers DESC
        """
        params = (state,)

    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql, params)
    finally:
        con.close()


def get_category_kpis(state: str | None = None) -> pd.DataFrame:
    if state is None or state == "All":
        sql = """
        SELECT
            category,
            total_orders,
            unique_products,
            items_sold,
            product_revenue,
            freight_revenue,
            gross_merchandise_value,
            avg_item_price
        FROM gold.category_kpis
        ORDER BY gross_merchandise_value DESC
        """
        params = ()
    else:
        sql = """
        SELECT
            category,
            total_orders,
            unique_products,
            items_sold,
            product_revenue,
            freight_revenue,
            gross_merchandise_value,
            avg_item_price
        FROM gold.state_category_kpis
        WHERE customer_state = ?
        ORDER BY gross_merchandise_value DESC
        """
        params = (state,)

    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql, params)
    finally:
        con.close()


def get_cohort_retention() -> pd.DataFrame:
    sql = """
    SELECT
        cohort_month,
        order_month,
        month_number,
        active_customers,
        cohort_size,
        retention_rate_pct
    FROM gold.cohort_retention
    ORDER BY cohort_month, month_number
    """
    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql)
    finally:
        con.close()


def get_customer_360() -> pd.DataFrame:
    sql = """
    SELECT
        customer_unique_id,
        first_order_date,
        last_order_date,
        order_count,
        total_revenue,
        avg_order_value,
        total_items,
        avg_review_score,
        customer_state,
        customer_city
    FROM gold.customer_360
    ORDER BY total_revenue DESC
    """
    con = connect(DB_PATH, read_only=True)
    try:
        return query_df(con, sql)
    finally:
        con.close()


from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH
from src.db import connect, query_df


def get_segment_summary(state: str | None = None) -> pd.DataFrame:
    if state is None or state == "All":
        sql = """
        SELECT
            segment,
            customers,
            segment_revenue,
            revenue_share_pct,
            avg_orders,
            avg_customer_value,
            avg_recency_days
        FROM gold.segment_summary
        ORDER BY segment_revenue DESC
        """
        params = ()
    else:
        sql = """
        SELECT
            segment,
            customers,
            segment_revenue,
            revenue_share_pct,
            avg_orders,
            avg_customer_value,
            avg_recency_days
        FROM gold.state_segment_summary
        WHERE customer_state = ?
        ORDER BY segment_revenue DESC
        """
        params = (state,)

    con = connect(DB_PATH, read_only=True)

    try:
        return query_df(con, sql, params)
    finally:
        con.close()

def get_business_insights() -> pd.DataFrame:
    sql = """
    SELECT
        insight_type,
        priority,
        headline,
        detail,
        metric_value,
        metric_label,
        recommended_action
    FROM gold.business_insights
    ORDER BY
        CASE priority
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            ELSE 3
        END,
        insight_type
    """

    con = connect(DB_PATH, read_only=True)

    try:
        return query_df(con, sql)
    finally:
        con.close()

def get_segment_recommendations(state: str | None = None) -> pd.DataFrame:
    segments = get_segment_summary(state)

    recommendations = {
        "Champions": (
            "Protect retention and increase wallet share.",
            "Prioritize loyalty benefits, premium offers, and cross-sell opportunities."
        ),
        "Loyal Customers": (
            "Strengthen repeat purchasing.",
            "Use personalized recommendations and targeted retention offers."
        ),
        "Potential Loyalists": (
            "Convert promising customers into habitual buyers.",
            "Encourage a second or third purchase with relevant follow-up offers."
        ),
        "At Risk": (
            "Reduce customer churn risk.",
            "Target recent high-value inactive customers with win-back campaigns."
        ),
        "Hibernating": (
            "Identify recoverable dormant customers.",
            "Test low-cost reactivation campaigns before increasing acquisition spend."
        ),
        "Needs Attention": (
            "Improve customer engagement.",
            "Investigate purchase frequency and value drivers before applying broad incentives."
        ),
    }

    segments["priority"] = segments["segment"].map(
        {
            "Champions": "Protect",
            "Loyal Customers": "Grow",
            "Potential Loyalists": "Convert",
            "At Risk": "Recover",
            "Hibernating": "Reactivate",
            "Needs Attention": "Investigate",
        }
    ).fillna("Review")

    segments["business_goal"] = segments["segment"].map(
        {key: value[0] for key, value in recommendations.items()}
    ).fillna("Review customer behavior")

    segments["recommended_action"] = segments["segment"].map(
        {key: value[1] for key, value in recommendations.items()}
    ).fillna("Investigate segment behavior before taking action")

    return segments
