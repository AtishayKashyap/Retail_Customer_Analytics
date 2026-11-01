"""Streamlit dashboard. Entry point for Streamlit Community Cloud (main file: src/app.py)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retail_analytics import queries
from retail_analytics.build import ensure_warehouse
from retail_analytics.config import CURRENCY_SYMBOL, MIN_COHORT_SIZE, Settings
from retail_analytics.report import run_delivery_analysis

st.set_page_config(page_title="Retail Customer Analytics", layout="wide")

SETTINGS = Settings.from_env()
ACCENT = "#2563eb"
SEGMENT_ORDER = [
    "Champions",
    "Loyal",
    "At Risk",
    "Promising",
    "New",
    "Needs Attention",
    "Lost High-Value",
    "Hibernating",
]


def money(value: float, decimals: int = 0) -> str:
    return f"{CURRENCY_SYMBOL} {value:,.{decimals}f}"


def money_short(value: float) -> str:
    for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= size:
            return f"{CURRENCY_SYMBOL} {value / size:.1f}{suffix}"
    return money(value)


@st.cache_resource(
    show_spinner="Building the warehouse from the Olist source files (first run only, about a minute)..."
)
def connection() -> duckdb.DuckDBPyConnection:
    ensure_warehouse(SETTINGS.raw_dir, SETTINGS.db_path)
    return duckdb.connect(str(SETTINGS.db_path), read_only=True)


def cursor() -> duckdb.DuckDBPyConnection:
    # One shared read-only connection; each rerun gets its own cursor (DuckDB cursors are cheap).
    return connection().cursor()


@st.cache_data
def cached(name: str, *args: object) -> pd.DataFrame:
    return getattr(queries, name)(cursor(), *args)


@st.cache_data
def delivery_test() -> dict[str, object]:
    report = SETTINGS.reports_dir / "delivery_review_test.json"
    if report.exists():
        return json.loads(report.read_text())
    return run_delivery_analysis(cursor(), iterations=300).to_dict()


def style(fig, height: int = 360):  # type: ignore[no-untyped-def]
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified")
    return fig


# --------------------------------------------------------------------------- layout
con = cursor()
st.title("Retail Customer Analytics")
st.caption(
    "Olist Brazilian e-commerce marketplace, 2016-2018 (about 99k orders). Amounts in Brazilian reais (R$). "
    "Revenue counts every order except canceled and unavailable ones."
)

scope = st.sidebar.selectbox(
    "Customer state", ["ALL", *queries.states(con)], format_func=lambda s: "All of Brazil" if s == "ALL" else s
)
st.sidebar.caption("Every view, including the KPIs and segments, is recomputed for the selected state.")

tabs = st.tabs(
    ["Overview", "Segments", "Categories", "Retention", "Delivery & Reviews", "Data Quality", "Customer Lookup"]
)

# --------------------------------------------------------------------------- overview
with tabs[0]:
    k = queries.scope_kpis(con, scope)
    first, second = st.columns(3), st.columns(3)
    first[0].metric("Orders", f"{int(k.orders):,}")
    first[1].metric("Customers", f"{int(k.customers):,}")
    first[2].metric("Revenue", money_short(k.revenue), help=money(k.revenue))
    second[0].metric("Average order value", money(k.avg_order_value, 2))
    second[1].metric("Repeat customers", f"{k.repeat_customer_rate:.1%}", help="Customers with 2+ valid orders")
    second[2].metric("Late deliveries", f"{k.late_delivery_rate:.1%}", help="Delivered after the promised date")

    st.subheader("Key findings")
    for headline, detail in queries.insights(con, scope):
        st.markdown(f"**{headline}**  \n{detail}")

    monthly = cached("monthly_kpis", scope)
    st.subheader("Monthly trend")
    st.caption("Partial months (the 2016 launch and the late-2018 cut-off, under 10% of a typical month) are excluded.")
    left, right = st.columns(2)
    left.plotly_chart(
        style(
            px.line(
                monthly,
                x="order_month",
                y="revenue",
                markers=True,
                title=f"Revenue ({CURRENCY_SYMBOL})",
                color_discrete_sequence=[ACCENT],
            )
        ).update_layout(xaxis_title=None, yaxis_title=None),
        width="stretch",
    )
    right.plotly_chart(
        style(
            px.line(
                monthly, x="order_month", y="orders", markers=True, title="Orders", color_discrete_sequence=[ACCENT]
            )
        ).update_layout(xaxis_title=None, yaxis_title=None),
        width="stretch",
    )

# --------------------------------------------------------------------------- segments
with tabs[1]:
    seg = cached("segment_summary", scope)
    seg["segment"] = pd.Categorical(seg["segment"], SEGMENT_ORDER, ordered=True)
    seg = seg.sort_values("segment")
    st.subheader("RFM segments")
    st.caption(
        "Recency and spend are scored in quintiles; frequency is used as a tier (one-time vs repeat), because 97% "
        "of customers order once and a frequency quintile would split identical customers at random."
    )
    left, right = st.columns(2)
    left.plotly_chart(
        style(
            px.bar(seg, x="segment", y="customers", title="Customers", color_discrete_sequence=[ACCENT])
        ).update_layout(xaxis_title=None, yaxis_title=None),
        width="stretch",
    )
    right.plotly_chart(
        style(
            px.bar(seg, x="segment", y="revenue_share", title="Share of revenue", color_discrete_sequence=[ACCENT])
        ).update_layout(xaxis_title=None, yaxis_title=None, yaxis_tickformat=".0%"),
        width="stretch",
    )
    st.dataframe(
        seg[
            [
                "segment",
                "customers",
                "customer_share",
                "revenue",
                "revenue_share",
                "avg_orders",
                "avg_customer_value",
                "avg_recency_days",
                "avg_review_score",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "customer_share": st.column_config.NumberColumn("customer share", format="percent"),
            "revenue_share": st.column_config.NumberColumn("revenue share", format="percent"),
            "revenue": st.column_config.NumberColumn(f"revenue ({CURRENCY_SYMBOL})", format="%.0f"),
            "avg_customer_value": st.column_config.NumberColumn(f"avg value ({CURRENCY_SYMBOL})", format="%.2f"),
            "avg_orders": st.column_config.NumberColumn(format="%.2f"),
            "avg_recency_days": st.column_config.NumberColumn("avg recency (days)", format="%.0f"),
            "avg_review_score": st.column_config.NumberColumn("avg review", format="%.2f"),
        },
    )
    with st.expander("Segment rules"):
        st.markdown(
            """
| Segment | Rule (R and M are quintiles 1-5, 5 = best) | Suggested action |
|---|---|---|
| Champions | repeat buyer, R >= 4, M >= 4 | Protect: early access, loyalty benefits |
| Loyal | repeat buyer, R >= 3 | Grow basket size with recommendations |
| At Risk | repeat buyer, R <= 2 | Win back before they lapse for good |
| Promising | one order, R >= 4, M >= 4 | Second-order incentive while the first is recent |
| New | one order, R >= 4 | Onboarding and follow-up offers |
| Needs Attention | one order, R = 3 | Re-engage with category-relevant offers |
| Lost High-Value | one order, R <= 2, M >= 4 | Targeted win-back on the category they bought |
| Hibernating | one order, R <= 2, M <= 3 | Low-cost reactivation only |
"""
        )

# --------------------------------------------------------------------------- categories
with tabs[2]:
    cats = cached("category_kpis", scope)
    top = cats.head(15).sort_values("gmv")
    st.subheader("Top categories by gross merchandise value")
    st.plotly_chart(
        style(px.bar(top, x="gmv", y="category", orientation="h", color_discrete_sequence=[ACCENT]), 480).update_layout(
            xaxis_title=f"GMV ({CURRENCY_SYMBOL})", yaxis_title=None, hovermode="closest"
        ),
        width="stretch",
    )
    st.dataframe(cats, hide_index=True, width="stretch")

# --------------------------------------------------------------------------- retention
with tabs[3]:
    cohorts = cached("cohort_retention")
    st.subheader("Repeat purchases by monthly cohort")
    st.caption(
        f"Share of each first-purchase cohort that ordered again N months later. Month 0 (always 100%) is omitted so "
        f"the colour scale shows the repeat behaviour. Cohorts under {MIN_COHORT_SIZE} customers and months after "
        "the data ends are left blank."
    )
    shown = cohorts[(cohorts.month_number > 0) & cohorts.is_reliable]
    pivot = shown.pivot(index="cohort_month", columns="month_number", values="retention_rate")
    pivot.index = pd.to_datetime(pivot.index).strftime("%Y-%m")
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        labels={"x": "Months since first purchase", "y": "Cohort", "color": "Retention"},
    )
    fig.update_coloraxes(colorbar_tickformat=".1%")
    st.plotly_chart(style(fig, 520).update_layout(hovermode="closest"), width="stretch")
    avg = shown.groupby("month_number", as_index=False)["retention_rate"].mean()
    st.caption(
        f"Average month-1 repeat rate: {avg.loc[avg.month_number == 1, 'retention_rate'].iloc[0]:.2%}. "
        "Olist is mostly a one-purchase marketplace, which is why retention, not acquisition, is the main lever."
    )

# --------------------------------------------------------------------------- delivery
with tabs[4]:
    t = delivery_test()
    st.subheader("Do late deliveries get worse reviews?")
    r = t["rank_biserial"]
    d = t["low_review_share_difference"]
    cols = st.columns(4)
    cols[0].metric("On-time orders", f"{t['n_on_time']:,}")
    cols[0].caption(f"mean review {t['mean_on_time']:.2f}")
    cols[1].metric("Late orders", f"{t['n_late']:,}")
    cols[1].caption(f"mean review {t['mean_late']:.2f}")
    cols[2].metric("Effect size (rank-biserial)", f"{r['estimate']:.2f}")
    cols[2].caption(f"95% CI {r['low']:.2f} to {r['high']:.2f}")
    cols[3].metric("Extra 1-2 star reviews when late", f"+{100 * d['estimate']:.1f} pp")
    cols[3].caption(f"95% CI {100 * d['low']:.1f} to {100 * d['high']:.1f} pp")
    st.markdown(f"**Result:** {t['interpretation']}")

    dist = cached("review_distribution")
    st.plotly_chart(
        style(
            px.bar(
                dist,
                x="stars",
                y="share",
                color="delivery_group",
                barmode="group",
                color_discrete_map={"On time": ACCENT, "Late": "#dc2626"},
                title="Review score distribution",
            )
        ).update_layout(yaxis_tickformat=".0%", hovermode="closest"),
        width="stretch",
    )
    with st.expander("Method and caveats"):
        st.markdown(
            """
- **Late** means delivered on a later calendar day than the promised date (Olist stores the promise as a date).
- Two-sided Mann-Whitney U test on order-level scores; the effect size is the rank-biserial correlation with a
  percentile bootstrap interval. A test on medians would be the wrong question for a 1-5 scale.
- With roughly 96k orders almost any difference is significant, so the effect size and the 1-2 star share are
  the numbers to read.
- Observational data: late orders differ in region, category and seller too, so this is association, not proof
  of cause. Olist also sends its survey around the promised date, so some late-order reviews were written before
  the parcel arrived.
"""
        )

# --------------------------------------------------------------------------- quality
with tabs[5]:
    checks = cached("quality_checks")
    errors = checks[(checks.severity == "error") & ~checks.passed]
    st.subheader("Data-quality checks")
    st.caption(
        "Run on every build. Any failed error-level check stops the build, so the dashboard only ever shows data "
        "that passed. Warnings are known properties of the source data."
    )
    cols = st.columns(3)
    cols[0].metric("Checks", len(checks))
    cols[1].metric("Errors", len(errors))
    cols[2].metric("Warnings", int(((checks.severity == "warning") & ~checks.passed).sum()))
    st.dataframe(checks, hide_index=True, width="stretch")

# --------------------------------------------------------------------------- lookup
with tabs[6]:
    st.subheader("Customer lookup")
    prefix = st.text_input(
        "Customer id (or the first few characters)", placeholder="e.g. 8d50f5eadf50201ccdcedfb9e2ac8455"
    )
    if prefix:
        matches = queries.search_customers(con, scope, prefix)
        st.caption(f"{len(matches)} match(es), top 50 by spend")
        st.dataframe(matches, hide_index=True, width="stretch")
        if len(matches) == 1 or (not matches.empty and matches.customer_unique_id.iloc[0] == prefix.strip()):
            cid = matches.customer_unique_id.iloc[0]
            p = queries.customer_profile(con, cid).iloc[0]
            st.markdown(f"**{p.customer_city.title()}, {p.customer_state}** · segment **{p.segment}**")
            cols = st.columns(4)
            cols[0].metric("Orders", int(p.frequency))
            cols[1].metric("Total spend", money(p.monetary_value, 2))
            cols[2].metric("Days since last order", int(p.recency_days))
            cols[3].metric("Scores (R / M)", f"{int(p.r_score)} / {int(p.m_score)}")
            st.dataframe(queries.customer_orders(con, cid), hide_index=True, width="stretch")
