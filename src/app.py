from pathlib import Path
import sys

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analytics import (
    get_category_kpis,
    get_business_insights,
    get_customer_detail,
    get_customer_profile,
    get_cohort_retention,
    get_customer_360,
    get_customer_segments,
    get_executive_kpis,
    get_segment_summary,
    get_segment_recommendations,
    get_monthly_kpis,
)


st.set_page_config(
    page_title="Retail Customer Analytics",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_executive():
    return get_executive_kpis()


@st.cache_data
def load_monthly(state):
    return get_monthly_kpis(state)


@st.cache_data
def load_segments(state):
    return get_customer_segments(state)


@st.cache_data
def load_segment_summary(state):
    return get_segment_summary(state)


@st.cache_data
def load_segment_recommendations(state):
    return get_segment_recommendations(state)


@st.cache_data
def load_business_insights():
    return get_business_insights()


@st.cache_data
def load_categories(state):
    return get_category_kpis(state)


@st.cache_data
def load_cohorts():
    return get_cohort_retention()


@st.cache_data
def load_customers():
    return get_customer_360()


st.title("Retail Customer Analytics Platform")
st.caption(
    "A decision-support dashboard for customer behavior, "
    "commercial performance, and retention."
)

# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

st.sidebar.header("Filters")

customers = load_customers()

states = sorted(
    customers["customer_state"]
    .dropna()
    .astype(str)
    .unique()
)

selected_state = st.sidebar.selectbox(
    "Customer State",
    ["All"] + states,
)

filtered_customers = customers.copy()

if selected_state != "All":
    filtered_customers = filtered_customers[
        filtered_customers["customer_state"].astype(str) == selected_state
    ]


# ---------------------------------------------------------------------
# Analytical data
# ---------------------------------------------------------------------

executive = load_executive()
monthly = load_monthly(selected_state)
segments = load_segments(selected_state)
segment_summary = load_segment_summary(selected_state)
segment_recommendations = load_segment_recommendations(selected_state)
business_insights = load_business_insights()
categories = load_categories(selected_state)
cohorts = load_cohorts()

if selected_state != "All":
    filtered_customers = filtered_customers[
        filtered_customers["customer_state"].astype(str) == selected_state
    ]


tabs = st.tabs(
    [
        "Executive",
        "Customer Segments",
        "Commercial",
        "Retention",
        "Customer Explorer",
    ]
)


# ---------------------------------------------------------------------
# Executive
# ---------------------------------------------------------------------

with tabs[0]:
    st.subheader("Executive Overview")

    st.markdown("### Key Findings")

    if selected_state != "All":
        st.caption(
            "These findings summarize the overall customer base; "
            "the KPI and trend views above respect the selected state."
        )

    for _, insight in business_insights.iterrows():
        priority = str(insight["priority"]).upper()

        with st.container(border=True):
            st.markdown(
                f"**{priority} · {insight['headline']}**"
            )
            st.write(insight["detail"])
            st.caption(
                f"Recommended action: {insight['recommended_action']}"
            )

    if selected_state == "All":
        row = executive.iloc[0]
    else:
        state_orders = filtered_customers["order_count"].sum()
        state_customers = len(filtered_customers)
        state_revenue = filtered_customers["total_revenue"].sum()

        row = {
            "total_orders": state_orders,
            "unique_customers": state_customers,
            "total_revenue": state_revenue,
            "avg_order_value": (
                state_revenue / state_orders
                if state_orders > 0
                else 0
            ),
            "avg_review_score": filtered_customers[
                "avg_review_score"
            ].mean(),
        }

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric(
        "Orders",
        f"{int(row['total_orders']):,}",
        help="Number of customer orders represented in the selected scope.",
    )

    col2.metric(
        "Customers",
        f"{int(row['unique_customers']):,}",
        help="Unique customers represented in the selected scope.",
    )

    col3.metric(
        "Revenue",
        f"₹{row['total_revenue']:,.0f}",
        help="Revenue from orders excluding canceled and unavailable orders.",
    )

    col4.metric(
        "Avg Order Value",
        f"₹{row['avg_order_value']:,.2f}",
        help="Average revenue per order.",
    )

    col5.metric(
        "Avg Review",
        f"{row['avg_review_score']:.2f}",
        help="Average review score.",
    )

    st.markdown("### Monthly Performance")

    chart_data = monthly.copy()

    if selected_state != "All":
        st.caption(f"Monthly trend for {selected_state}")

    fig = px.line(
        chart_data,
        x="order_month",
        y="revenue",
        markers=True,
        title="Monthly Revenue",
    )

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Revenue",
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")

    col1, col2 = st.columns(2)

    with col1:
        fig_orders = px.line(
            chart_data,
            x="order_month",
            y="total_orders",
            markers=True,
            title="Monthly Orders",
        )
        fig_orders.update_layout(
            xaxis_title="Month",
            yaxis_title="Orders",
        )
        st.plotly_chart(fig_orders, width="stretch")

    with col2:
        fig_customers = px.line(
            chart_data,
            x="order_month",
            y="unique_customers",
            markers=True,
            title="Monthly Active Customers",
        )
        fig_customers.update_layout(
            xaxis_title="Month",
            yaxis_title="Customers",
        )
        st.plotly_chart(fig_customers, width="stretch")


# ---------------------------------------------------------------------
# Customer Segments
# ---------------------------------------------------------------------

with tabs[1]:
    st.subheader("Customer Segmentation")

    if selected_state != "All":
        st.caption(f"Customer segments for {selected_state}")

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            segments,
            x="segment",
            y="customers",
            title="Customers by Segment",
        )
        fig.update_layout(
            xaxis_title="Segment",
            yaxis_title="Customers",
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig = px.bar(
            segments,
            x="segment",
            y="avg_customer_value",
            title="Average Customer Value by Segment",
        )
        fig.update_layout(
            xaxis_title="Segment",
            yaxis_title="Average Customer Value",
        )
        st.plotly_chart(fig, width="stretch")

    st.markdown("### Segment Business Value")

    summary = segment_summary.copy()

    if selected_state != "All":
        state_customers = set(
            filtered_customers["customer_unique_id"]
        )

        # Segment summary is currently global.
        # State-specific segment metrics are shown from the
        # state-filtered customer-level segment data above.
        st.caption(
            "Revenue-share metrics below represent the overall customer base."
        )

    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Recommended Actions")

    for _, recommendation in segment_recommendations.iterrows():
        with st.container(border=True):
            st.markdown(
                f"**{recommendation['segment']} · "
                f"{recommendation['priority']}**"
            )
            st.write(recommendation["business_goal"])
            st.caption(
                f"Action: {recommendation['recommended_action']}"
            )


# ---------------------------------------------------------------------
# Commercial
# ---------------------------------------------------------------------

with tabs[2]:
    st.subheader("Commercial Performance")

    if selected_state != "All":
        st.caption(f"Category performance for {selected_state}")

    top_categories = categories.head(15).copy()

    fig = px.bar(
        top_categories.sort_values("gross_merchandise_value"),
        x="gross_merchandise_value",
        y="category",
        orientation="h",
        title="Top Categories by Gross Merchandise Value",
    )

    fig.update_layout(
        xaxis_title="Gross Merchandise Value",
        yaxis_title="Category",
    )

    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        categories,
        width="stretch",
        hide_index=True,
    )


# ---------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------

with tabs[3]:
    st.subheader("Cohort Retention")

    if cohorts.empty:
        st.info("No cohort data available.")
    else:
        pivot = cohorts.pivot(
            index="cohort_month",
            columns="month_number",
            values="retention_rate_pct",
        )

        fig = px.imshow(
            pivot,
            labels={
                "x": "Months Since First Purchase",
                "y": "Customer Cohort",
                "color": "Retention %",
            },
            aspect="auto",
            title="Customer Retention by Cohort",
        )

        st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------------
# Customer Explorer
# ---------------------------------------------------------------------

with tabs[4]:
    st.subheader("Customer Explorer")

    search = st.text_input(
        "Search customer ID",
        placeholder="Enter a customer ID...",
    )

    display = filtered_customers.copy()

    if search:
        display = display[
            display["customer_unique_id"]
            .astype(str)
            .str.contains(search, case=False, na=False)
        ]

    st.write(f"Showing {len(display):,} customers")

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Customer Drill-down")

    selected_customer = st.text_input(
        "Enter an exact customer ID",
        placeholder="Customer UUID",
        key="customer_drilldown",
    )

    if selected_customer:
        profile = get_customer_profile(selected_customer)

        if profile.empty:
            st.warning("Customer ID not found.")
        else:
            customer = profile.iloc[0]

            st.markdown(
                f"**{customer['customer_city']}, {customer['customer_state']}** "
                f"· Segment: **{customer['segment']}**"
            )

            col1, col2, col3, col4, col5 = st.columns(5)

            col1.metric(
                "RFM Score",
                f"{int(customer['rfm_score'])}"
            )

            col2.metric(
                "Recency",
                f"{int(customer['recency_days'])} days"
            )

            col3.metric(
                "Orders",
                f"{int(customer['frequency'])}"
            )

            col4.metric(
                "Customer Value",
                f"₹{customer['monetary_value']:,.2f}"
            )

            col5.metric(
                "Avg Review",
                f"{customer['avg_review_score']:.2f}"
            )

            history = get_customer_detail(selected_customer)

            st.markdown("### Order History")

            st.dataframe(
                history,
                width="stretch",
                hide_index=True,
            )













