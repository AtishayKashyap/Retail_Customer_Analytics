"""Read-side queries used by the dashboard. Every function takes an open connection and a scope
('ALL' or a two-letter state), and returns a DataFrame computed in DuckDB."""

from __future__ import annotations

import duckdb
import pandas as pd

ALL = "ALL"


def _df(con: duckdb.DuckDBPyConnection, sql: str, params: list[object] | None = None) -> pd.DataFrame:
    return con.execute(sql, params or []).df()


def states(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [
        r[0]
        for r in con.execute("SELECT scope FROM gold.mart_scope_kpis WHERE scope <> 'ALL' ORDER BY scope").fetchall()
    ]


def scope_kpis(con: duckdb.DuckDBPyConnection, scope: str) -> pd.Series:
    df = _df(con, "SELECT * FROM gold.mart_scope_kpis WHERE scope = ?", [scope])
    return df.iloc[0]


def monthly_kpis(con: duckdb.DuckDBPyConnection, scope: str, include_partial: bool = False) -> pd.DataFrame:
    return _df(
        con,
        "SELECT * FROM gold.mart_monthly_kpis WHERE scope = ? AND (? OR NOT is_partial) ORDER BY order_month",
        [scope, include_partial],
    )


def segment_summary(con: duckdb.DuckDBPyConnection, scope: str) -> pd.DataFrame:
    return _df(con, "SELECT * FROM gold.mart_segment_summary WHERE scope = ? ORDER BY revenue DESC", [scope])


def category_kpis(con: duckdb.DuckDBPyConnection, scope: str, limit: int | None = None) -> pd.DataFrame:
    sql = "SELECT * EXCLUDE (scope) FROM gold.mart_category_kpis WHERE scope = ? ORDER BY gmv DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return _df(con, sql, [scope])


def cohort_retention(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _df(con, "SELECT * FROM gold.mart_cohort_retention ORDER BY cohort_month, month_number")


def delivery_review(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _df(con, "SELECT delivery_group, review_score, delivery_delay_days FROM gold.delivery_review")


def review_distribution(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _df(
        con,
        """
        WITH counts AS (
            SELECT delivery_group, round(review_score)::INT AS stars, COUNT(*) AS orders
            FROM gold.delivery_review
            GROUP BY ALL
        )
        SELECT *, orders / SUM(orders) OVER (PARTITION BY delivery_group) AS share
        FROM counts
        ORDER BY delivery_group, stars
        """,
    )


def quality_checks(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    return _df(con, "SELECT * FROM quality.check_results ORDER BY passed, severity, check_group, check_name")


def search_customers(con: duckdb.DuckDBPyConnection, scope: str, prefix: str, limit: int = 50) -> pd.DataFrame:
    return _df(
        con,
        """
        SELECT customer_unique_id, customer_state, customer_city, segment, frequency, monetary_value,
               recency_days, last_purchase_date
        FROM gold.mart_rfm
        WHERE (? = 'ALL' OR customer_state = ?) AND customer_unique_id LIKE ? || '%'
        ORDER BY monetary_value DESC
        LIMIT ?
        """,
        [scope, scope, prefix.strip().lower(), limit],
    )


def customer_profile(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> pd.DataFrame:
    return _df(con, "SELECT * FROM gold.mart_rfm WHERE customer_unique_id = ?", [customer_unique_id.strip()])


def customer_orders(con: duckdb.DuckDBPyConnection, customer_unique_id: str) -> pd.DataFrame:
    return _df(
        con,
        """
        SELECT order_id, order_status, purchased_at, delivered_at, estimated_delivery_date, is_late,
               order_value, item_count, review_score
        FROM gold.fct_orders
        WHERE customer_unique_id = ?
        ORDER BY purchased_at DESC
        """,
        [customer_unique_id.strip()],
    )


def insights(con: duckdb.DuckDBPyConnection, scope: str) -> list[tuple[str, str]]:
    """Headline findings for the scope, each derived from a mart (headline, detail)."""
    k = scope_kpis(con, scope)
    seg = segment_summary(con, scope).set_index("segment")
    top_cat = category_kpis(con, scope, limit=1)
    repeat_revenue = seg.loc[seg["avg_orders"] > 1.5, "revenue"].sum() / seg["revenue"].sum()

    findings = [
        (
            f"{k.repeat_customer_rate:.1%} of customers came back for a second order",
            f"Repeat buyers generate {repeat_revenue:.1%} of revenue. Converting one-time buyers "
            "is the largest growth lever in this data.",
        ),
    ]
    gap = con.execute(
        """
        SELECT AVG(review_score) FILTER (WHERE delivery_group = 'On time')
             - AVG(review_score) FILTER (WHERE delivery_group = 'Late')
        FROM gold.delivery_review WHERE ? = 'ALL' OR order_state = ?
        """,
        [scope, scope],
    ).fetchone()
    if gap and gap[0] is not None:
        findings.append(
            (
                f"{k.late_delivery_rate:.1%} of delivered orders arrived after the promised date",
                f"Late orders average {gap[0]:.1f} stars lower in reviews than on-time orders.",
            )
        )
    if not top_cat.empty:
        c = top_cat.iloc[0]
        findings.append(
            (f"{c.category.replace('_', ' ').title()} is the largest category by GMV", f"{int(c.orders):,} orders.")
        )
    for name in ("Promising", "Lost High-Value"):
        if name in seg.index:
            s = seg.loc[name]
            findings.append(
                (
                    f"{name}: {s.customers:,} customers, {s.revenue_share:.1%} of revenue",
                    f"Top-40% spenders who bought once, {s.avg_recency_days:.0f} days ago on average; "
                    + (
                        "recent enough to target for a second order." if name == "Promising" else "a win-back audience."
                    ),
                )
            )
    return findings
